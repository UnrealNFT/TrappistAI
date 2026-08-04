from payment_gate import create_payment_challenge, verify_payment_proof


def test_valid_proof_is_accepted():
    token = create_payment_challenge("/api/v1/demo", 5, currency="CSPR", ttl_seconds=60)
    proof = {"receipt": {"status": "confirmed", "amount": 5, "currency": "CSPR"}}

    assert verify_payment_proof(token, proof) is True


def test_expired_or_invalid_proof_is_rejected():
    token = create_payment_challenge("/api/v1/demo", 5, currency="CSPR", ttl_seconds=0)
    proof = {"receipt": {"status": "confirmed", "amount": 4, "currency": "CSPR"}}

    assert verify_payment_proof(token, proof) is False
