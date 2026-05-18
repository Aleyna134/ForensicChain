import uuid
import datetime
import logging
from sqlalchemy import text
from sqlalchemy.orm import Session
import ledger_pb2
import ledger_pb2_grpc
from db.database import SessionLocal
from db.models import LedgerRecord, LedgerState
from chain.hash_chain import create_hash_chain_entry, compute_payload_hash, compute_record_hash

logger = logging.getLogger(__name__)

class LedgerServicer(ledger_pb2_grpc.LedgerServiceServicer):
    
    def _append_record(self, raw_payload: dict, artifact_id: str, case_id: str, record_type: str, 
                       hash_algorithm=None, hash_value=None, signature_algorithm=None, signature_value=None, signer_id=None):
        with SessionLocal() as db:
            try:
                # Lock the state row for concurrency
                state_query = text("SELECT last_record_hash FROM ledger_state WHERE id = 1 FOR UPDATE")
                result = db.execute(state_query).mappings().fetchone()
                
                if result:
                    previous_record_hash = result["last_record_hash"]
                else:
                    previous_record_hash = None
                    # Attempt to insert initial state if missing
                    db.execute(text("INSERT INTO ledger_state (id, last_record_hash) VALUES (1, NULL) ON CONFLICT (id) DO NOTHING"))

                # Compute hashes
                payload_hash, record_hash = create_hash_chain_entry(raw_payload, previous_record_hash)
                record_id = uuid.uuid4()
                now = datetime.datetime.now(datetime.timezone.utc)

                # Insert ledger record
                new_record = LedgerRecord(
                    record_id=record_id,
                    artifact_id=uuid.UUID(artifact_id),
                    case_id=case_id,
                    record_type=record_type,
                    hash_algorithm=hash_algorithm,
                    hash_value=hash_value,
                    signature_algorithm=signature_algorithm,
                    signature_value=signature_value,
                    signer_id=signer_id,
                    payload_hash=payload_hash,
                    previous_record_hash=previous_record_hash,
                    record_hash=record_hash,
                    raw_payload=raw_payload,
                    created_at=now
                )
                db.add(new_record)

                # Update ledger state
                update_state = text("UPDATE ledger_state SET last_record_hash = :h, updated_at = :now WHERE id = 1")
                db.execute(update_state, {"h": record_hash, "now": now})
                
                db.commit()
                
                return ledger_pb2.ProofRecordResponse(
                    record_id=str(record_id),
                    artifact_id=artifact_id,
                    record_type=record_type,
                    payload_hash=payload_hash,
                    previous_record_hash=previous_record_hash or "",
                    record_hash=record_hash,
                    created_at=now.isoformat(),
                    success=True,
                    error_message=""
                )
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to append record: {e}")
                return ledger_pb2.ProofRecordResponse(
                    artifact_id=artifact_id,
                    record_type=record_type,
                    success=False,
                    error_message=str(e)
                )

    def AppendProofRecord(self, request, context):
        payload = {
            "artifact_id": request.artifact_id,
            "case_id": request.case_id,
            "record_type": request.record_type,
            "hash_algorithm": request.hash_algorithm,
            "hash_value": request.hash_value,
            "signature_algorithm": request.signature_algorithm,
            "signature_value": request.signature_value,
            "signer_id": request.signer_id,
            "created_at": request.created_at
        }
        
        return self._append_record(
            raw_payload=payload,
            artifact_id=request.artifact_id,
            case_id=request.case_id,
            record_type=request.record_type,
            hash_algorithm=request.hash_algorithm,
            hash_value=request.hash_value,
            signature_algorithm=request.signature_algorithm,
            signature_value=request.signature_value,
            signer_id=request.signer_id
        )

    def AppendVerificationRecord(self, request, context):
        payload = {
            "artifact_id": request.artifact_id,
            "case_id": request.case_id,
            "record_type": request.record_type,
            "verification_result": request.verification_result,
            "original_hash": request.original_hash,
            "current_hash": request.current_hash,
            "verified_by": request.verified_by,
            "verified_at": request.verified_at
        }
        
        return self._append_record(
            raw_payload=payload,
            artifact_id=request.artifact_id,
            case_id=request.case_id,
            record_type=request.record_type
        )

    def GetProofByArtifactId(self, request, context):
        try:
            with SessionLocal() as db:
                record = db.query(LedgerRecord)\
                           .filter(LedgerRecord.artifact_id == uuid.UUID(request.artifact_id), 
                                   LedgerRecord.record_type == "EVIDENCE_PROOF_CREATED")\
                           .order_by(LedgerRecord.created_at.desc())\
                           .first()
                if not record:
                    return ledger_pb2.ArtifactIntegrityProofResponse(
                        success=False,
                        error_message="Proof record not found"
                    )

                return ledger_pb2.ArtifactIntegrityProofResponse(
                    record_id=str(record.record_id),
                    artifact_id=str(record.artifact_id),
                    case_id=record.case_id,
                    hash_algorithm=record.hash_algorithm,
                    hash_value=record.hash_value,
                    signature_algorithm=record.signature_algorithm,
                    signature_value=record.signature_value,
                    signer_id=record.signer_id,
                    record_hash=record.record_hash,
                    success=True,
                    error_message=""
                )
        except Exception as e:
            return ledger_pb2.ArtifactIntegrityProofResponse(
                success=False,
                error_message=str(e)
            )

    def ValidateLedgerChain(self, request, context):
        try:
            with SessionLocal() as db:
                records = db.query(LedgerRecord).order_by(LedgerRecord.created_at.asc()).all()
                
                checked_records = 0
                expected_prev_hash = None
                
                for record in records:
                    # 1. Verify previous hash continuity
                    if record.previous_record_hash != expected_prev_hash:
                        return ledger_pb2.ValidateLedgerResponse(
                            chain_valid=False,
                            checked_records=checked_records,
                            error_message=f"Broken chain at record {record.record_id}: expected prev_hash {expected_prev_hash}, got {record.previous_record_hash}"
                        )
                    
                    # 2. Recompute hashes from raw_payload
                    recomputed_payload_hash = compute_payload_hash(record.raw_payload)
                    if recomputed_payload_hash != record.payload_hash:
                        return ledger_pb2.ValidateLedgerResponse(
                            chain_valid=False,
                            checked_records=checked_records,
                            error_message=f"Corrupted payload hash at record {record.record_id}"
                        )
                        
                    recomputed_record_hash = compute_record_hash(recomputed_payload_hash, record.previous_record_hash)
                    if recomputed_record_hash != record.record_hash:
                        return ledger_pb2.ValidateLedgerResponse(
                            chain_valid=False,
                            checked_records=checked_records,
                            error_message=f"Corrupted record hash at record {record.record_id}"
                        )
                        
                    expected_prev_hash = record.record_hash
                    checked_records += 1
                
                return ledger_pb2.ValidateLedgerResponse(
                    chain_valid=True,
                    checked_records=checked_records,
                    error_message=""
                )
        except Exception as e:
             return ledger_pb2.ValidateLedgerResponse(
                 chain_valid=False,
                 checked_records=0,
                 error_message=str(e)
             )
