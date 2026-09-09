"""Dead Letter Queue for audit logging and compliance tracking."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import asdict

from taparash.config import FilterResult


class DeadLetterQueue:
    """
    SQLite-based audit log for rejected chunks.

    Provides compliance tracking and rejection analysis for
    GDPR, HIPAA, and other regulatory requirements.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize Dead Letter Queue.

        Args:
            db_path: Path to SQLite database (default: ./taparash_dlq.db)
        """
        self.db_path = db_path or "taparash_dlq.db"
        self._init_database()

    def _init_database(self):
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rejected_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                original_text TEXT NOT NULL,
                processed_text TEXT,
                reason_code TEXT NOT NULL,
                reason_detail TEXT,
                metadata TEXT,
                text_length INTEGER,
                pii_masked_count INTEGER,
                entropy REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reason_code
            ON rejected_chunks(reason_code)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON rejected_chunks(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at
            ON rejected_chunks(created_at)
        """)

        conn.commit()
        conn.close()

    def log_rejection(self, result: FilterResult):
        """
        Log a rejected chunk to the DLQ.

        Args:
            result: FilterResult object for rejected chunk
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        timestamp = datetime.now().isoformat()
        metadata_json = json.dumps(result.metadata)

        cursor.execute("""
            INSERT INTO rejected_chunks (
                timestamp, original_text, processed_text,
                reason_code, reason_detail, metadata,
                text_length, pii_masked_count, entropy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            result.original_text,
            result.text,
            result.reason_code,
            result.reason_detail,
            metadata_json,
            len(result.original_text),
            result.metadata.get('pii_masked_count', 0),
            result.metadata.get('entropy')
        ))

        conn.commit()
        conn.close()

    def log_batch(self, rejected_results: List[FilterResult]):
        """
        Log multiple rejected chunks in a single transaction.

        Args:
            rejected_results: List of FilterResult objects
        """
        if not rejected_results:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        timestamp = datetime.now().isoformat()

        for result in rejected_results:
            metadata_json = json.dumps(result.metadata)

            cursor.execute("""
                INSERT INTO rejected_chunks (
                    timestamp, original_text, processed_text,
                    reason_code, reason_detail, metadata,
                    text_length, pii_masked_count, entropy
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                result.original_text,
                result.text,
                result.reason_code,
                result.reason_detail,
                metadata_json,
                len(result.original_text),
                result.metadata.get('pii_masked_count', 0),
                result.metadata.get('entropy')
            ))

        conn.commit()
        conn.close()

    def get_rejection_stats(self) -> Dict[str, int]:
        """
        Get statistics on rejection reasons.

        Returns:
            Dictionary mapping reason codes to counts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT reason_code, COUNT(*) as count
            FROM rejected_chunks
            GROUP BY reason_code
            ORDER BY count DESC
        """)

        stats = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()

        return stats

    def get_recent_rejections(self, limit: int = 100) -> List[Dict]:
        """
        Get most recent rejections.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of rejection records as dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM rejected_chunks
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

    def get_rejections_by_reason(self, reason_code: str, limit: int = 100) -> List[Dict]:
        """
        Get rejections for a specific reason code.

        Args:
            reason_code: Rejection reason code
            limit: Maximum number of records to return

        Returns:
            List of rejection records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM rejected_chunks
            WHERE reason_code = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (reason_code, limit))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

    def get_pii_violations(self, limit: int = 100) -> List[Dict]:
        """
        Get chunks rejected due to PII (had PII masked but still rejected).

        Args:
            limit: Maximum number of records to return

        Returns:
            List of records with PII detected
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM rejected_chunks
            WHERE pii_masked_count > 0
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

    def get_total_rejections(self) -> int:
        """
        Get total count of rejected chunks.

        Returns:
            Total number of rejections logged
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM rejected_chunks")
        count = cursor.fetchone()[0]

        conn.close()
        return count

    def clear_old_records(self, days: int = 90):
        """
        Delete records older than specified days.

        Args:
            days: Number of days to retain (default: 90)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM rejected_chunks
            WHERE created_at < datetime('now', '-' || ? || ' days')
        """, (days,))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted

    def export_to_json(self, output_path: str, reason_code: Optional[str] = None):
        """
        Export DLQ records to JSON file.

        Args:
            output_path: Path to output JSON file
            reason_code: Optional filter by reason code
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if reason_code:
            cursor.execute("""
                SELECT * FROM rejected_chunks
                WHERE reason_code = ?
                ORDER BY created_at DESC
            """, (reason_code,))
        else:
            cursor.execute("""
                SELECT * FROM rejected_chunks
                ORDER BY created_at DESC
            """)

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        return len(results)

    def print_summary(self):
        """Print DLQ summary statistics."""
        stats = self.get_rejection_stats()
        total = self.get_total_rejections()

        print("=" * 60)
        print("DEAD LETTER QUEUE SUMMARY")
        print("=" * 60)
        print(f"Total Rejections: {total}")
        print()
        print("Rejection Breakdown:")
        for reason, count in stats.items():
            percentage = (count / total * 100) if total > 0 else 0
            print(f"  {reason:20s}: {count:6d} ({percentage:5.1f}%)")
        print("=" * 60)
