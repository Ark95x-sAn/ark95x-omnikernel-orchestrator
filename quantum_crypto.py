"""
Quantum Cryptography System
============================
Encryption and key derivation based on Julian date and quantum signature.

Provides:
- Key derivation from Julian date base layer
- Symmetric encryption for data at rest
- Key rotation schedules
- Secure random number generation
"""

import hashlib
import hmac
import secrets
import base64
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend

from quantum_signature import get_quantum_signature


class QuantumCrypto:
    """
    Cryptographic system anchored to quantum signature.

    All key derivation starts from Julian date calculation of birth timestamp,
    ensuring unique and deterministic base entropy.
    """

    def __init__(self):
        """Initialize quantum crypto system."""
        self.signature = get_quantum_signature()
        self.julian_date = self.signature.get_julian_date()
        self.genesis_hash = self.signature.genesis_hash

        # Derive master encryption key from Julian date
        self.master_key = self._derive_master_key()

    def _derive_master_key(self) -> bytes:
        """
        Derive master encryption key from Julian date.

        Uses PBKDF2 with Julian date as password and genesis hash as salt.

        Returns:
            32-byte master key
        """
        # Convert Julian date to bytes (password)
        password = str(self.julian_date).encode()

        # Use genesis hash as salt
        salt = bytes.fromhex(self.genesis_hash)[:32]

        # Derive key using PBKDF2
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )

        return kdf.derive(password)

    def derive_key(
        self,
        purpose: str,
        context: Optional[str] = None,
        key_size: int = 32
    ) -> bytes:
        """
        Derive purpose-specific key from master key.

        Args:
            purpose: Key purpose identifier
            context: Optional context for key derivation
            key_size: Size of derived key in bytes

        Returns:
            Derived key bytes
        """
        # Combine purpose and context
        info = purpose.encode()
        if context:
            info += b':' + context.encode()

        # Use HMAC-based key derivation
        derived = hmac.new(
            self.master_key,
            info,
            hashlib.sha256
        ).digest()

        # Extend key if needed
        while len(derived) < key_size:
            derived += hmac.new(
                self.master_key,
                derived + info,
                hashlib.sha256
            ).digest()

        return derived[:key_size]

    def create_fernet_key(self, purpose: str) -> bytes:
        """
        Create Fernet-compatible encryption key for purpose.

        Args:
            purpose: Key purpose identifier

        Returns:
            Base64-encoded Fernet key
        """
        # Derive 32-byte key
        key = self.derive_key(purpose, key_size=32)

        # Fernet requires base64-encoded 32-byte key
        return base64.urlsafe_b64encode(key)

    def encrypt(self, data: bytes, purpose: str, context: Optional[str] = None) -> bytes:
        """
        Encrypt data using purpose-derived key.

        Args:
            data: Data to encrypt
            purpose: Encryption purpose
            context: Optional context

        Returns:
            Encrypted data (Fernet token)
        """
        # Derive Fernet key
        fernet_key = self.create_fernet_key(f"{purpose}:{context or 'default'}")

        # Create cipher
        cipher = Fernet(fernet_key)

        # Encrypt
        return cipher.encrypt(data)

    def decrypt(self, token: bytes, purpose: str, context: Optional[str] = None) -> bytes:
        """
        Decrypt data using purpose-derived key.

        Args:
            token: Encrypted token
            purpose: Encryption purpose
            context: Optional context

        Returns:
            Decrypted data

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails
        """
        # Derive Fernet key
        fernet_key = self.create_fernet_key(f"{purpose}:{context or 'default'}")

        # Create cipher
        cipher = Fernet(fernet_key)

        # Decrypt
        return cipher.decrypt(token)

    def encrypt_string(self, text: str, purpose: str, context: Optional[str] = None) -> str:
        """
        Encrypt string and return base64-encoded result.

        Args:
            text: String to encrypt
            purpose: Encryption purpose
            context: Optional context

        Returns:
            Base64-encoded encrypted token
        """
        encrypted = self.encrypt(text.encode(), purpose, context)
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt_string(self, token: str, purpose: str, context: Optional[str] = None) -> str:
        """
        Decrypt base64-encoded token to string.

        Args:
            token: Base64-encoded encrypted token
            purpose: Encryption purpose
            context: Optional context

        Returns:
            Decrypted string
        """
        encrypted = base64.urlsafe_b64decode(token.encode())
        decrypted = self.decrypt(encrypted, purpose, context)
        return decrypted.decode()

    def generate_secure_token(self, length: int = 32) -> str:
        """
        Generate cryptographically secure random token.

        Combines quantum signature entropy with system randomness.

        Args:
            length: Token length in bytes

        Returns:
            Hex-encoded secure token
        """
        # Mix quantum signature with system randomness
        quantum_bytes = hashlib.sha256(
            f"{self.genesis_hash}{secrets.token_hex(16)}".encode()
        ).digest()

        system_bytes = secrets.token_bytes(length)

        # XOR combine
        combined = bytes(q ^ s for q, s in zip(quantum_bytes[:length], system_bytes))

        return combined.hex()

    def create_signature(self, message: bytes, purpose: str = "default") -> str:
        """
        Create HMAC signature for message.

        Args:
            message: Message to sign
            purpose: Signing purpose

        Returns:
            Hex-encoded signature
        """
        key = self.derive_key(purpose)
        signature = hmac.new(key, message, hashlib.sha256).digest()
        return signature.hex()

    def verify_signature(
        self,
        message: bytes,
        signature: str,
        purpose: str = "default"
    ) -> bool:
        """
        Verify HMAC signature for message.

        Args:
            message: Original message
            signature: Hex-encoded signature
            purpose: Signing purpose

        Returns:
            True if signature is valid
        """
        expected = self.create_signature(message, purpose)
        return hmac.compare_digest(expected, signature)

    def get_key_rotation_schedule(
        self,
        purpose: str,
        rotation_days: int = 90
    ) -> Dict[str, Any]:
        """
        Get key rotation schedule for purpose.

        Based on quantum signature temporal anchor with configurable rotation.

        Args:
            purpose: Key purpose
            rotation_days: Days between rotations

        Returns:
            Dict with rotation schedule info
        """
        # Calculate birth date from temporal anchor
        birth_timestamp = self.signature.get_master_seed()
        birth_date = datetime.fromtimestamp(birth_timestamp)

        # Calculate next rotation from today
        today = datetime.now()
        days_since_birth = (today - birth_date).days

        # How many rotations have occurred?
        rotations_completed = days_since_birth // rotation_days

        # Next rotation date
        next_rotation = birth_date + timedelta(days=(rotations_completed + 1) * rotation_days)

        # Current key generation (epoch)
        current_epoch = rotations_completed

        return {
            'purpose': purpose,
            'current_epoch': current_epoch,
            'rotation_days': rotation_days,
            'last_rotation': birth_date + timedelta(days=rotations_completed * rotation_days),
            'next_rotation': next_rotation,
            'days_until_rotation': (next_rotation - today).days,
        }

    def get_rotated_key(self, purpose: str, epoch: Optional[int] = None) -> bytes:
        """
        Get key for specific rotation epoch.

        Args:
            purpose: Key purpose
            epoch: Rotation epoch (None = current)

        Returns:
            Epoch-specific key
        """
        if epoch is None:
            schedule = self.get_key_rotation_schedule(purpose)
            epoch = schedule['current_epoch']

        # Include epoch in derivation context
        return self.derive_key(purpose, context=f"epoch_{epoch}")

    def get_crypto_stats(self) -> Dict[str, Any]:
        """
        Get cryptography system statistics.

        Returns:
            Dict with crypto system info
        """
        return {
            'julian_date': self.julian_date,
            'genesis_hash': self.genesis_hash,
            'master_key_length': len(self.master_key),
            'birth_timestamp': self.signature.get_master_seed(),
            'solar_degree': self.signature.get_solar_degree(),
        }


# Singleton instance
_crypto_instance = None

def get_quantum_crypto() -> QuantumCrypto:
    """
    Get or create singleton quantum crypto instance.

    Returns:
        QuantumCrypto: Global crypto instance
    """
    global _crypto_instance
    if _crypto_instance is None:
        _crypto_instance = QuantumCrypto()
    return _crypto_instance
