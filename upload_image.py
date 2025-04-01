#!/usr/bin/env python3
import argparse
import hashlib
import os
import concurrent.futures
import random
import requests
import sys
from typing import Dict, Any, Tuple, List


class ImageUploader:
    """Image uploader class, handles proof of work and image upload process"""

    def __init__(self, endpoint: str):
        """Initialize uploader

        Args:
            endpoint: API endpoint address
        """
        self.endpoint = endpoint

    def get_challenge(self) -> Dict[str, Any]:
        """Get proof of work challenge from server"""
        response = requests.get(f"{self.endpoint}/api2/challenge")
        print(response.text)
        if response.status_code != 200:
            print(f"Failed to get challenge: {response.status_code}")
            sys.exit(1)

        data = response.json()
        if not data.get("success"):
            print("Challenge request failed")
            sys.exit(1)

        return data

    def find_suffix(self, pref: str, n: int, task_id: str) -> str:
        """Find valid suffix using multi-threading

        Args:
            pref: Prefix provided by server
            n: Difficulty level, hash must have N leading zero bits
            task_id: Task ID

        Returns:
            Valid suffix found
        """
        def is_valid_hash(hash_bytes: bytes, n: int) -> bool:
            """Check if hash has N leading zero bits

            Args:
                hash_bytes: Hash byte array
                n: Number of bits to check

            Returns:
                True if first N bits are zero
            """
            # Check full bytes
            full_bytes = n // 8
            for i in range(full_bytes):
                if hash_bytes[i] != 0:
                    return False

            # Check remaining bits
            remaining_bits = n % 8
            if remaining_bits > 0:
                # Create mask, e.g. for 3 bits, mask would be 1110 0000 (0xE0)
                mask = (0xFF << (8 - remaining_bits)) & 0xFF
                return (hash_bytes[full_bytes] & mask) == 0

            return True

        def worker(worker_id: int) -> Tuple[bool, str]:
            """Worker thread function to find valid suffix"""
            # Set random seed to ensure different threads generate different random numbers
            random.seed(os.urandom(4) + worker_id.to_bytes(4, 'little'))

            attempts = 0
            while True:
                # Generate 64-byte random suffix
                suff = bytes([random.randint(0, 255) for _ in range(64)]).hex()

                # Calculate SHA-256 hash of pref+suff
                combined = pref + suff
                hash_result = hashlib.sha256(bytes.fromhex(combined)).digest()

                # Check if first N bits are zero
                if is_valid_hash(hash_result, n):
                    return True, suff

                attempts += 1
                if attempts % 10000 == 0:
                    print(f"Thread {worker_id} has tried {attempts} times...")

        print(
            f"Starting proof of work calculation (difficulty N = {n} bits)...")

        # Use CPU core count for thread number
        with concurrent.futures.ThreadPoolExecutor() as executor:
            num_workers = min(32, (os.cpu_count() or 5) - 1)
            futures = [executor.submit(worker, i) for i in range(num_workers)]

            for future in concurrent.futures.as_completed(futures):
                success, suff = future.result()
                if success:
                    print(f"Valid suffix found!")
                    return suff

        return ""  # Theoretically won't reach here

    def upload_image(self, path: str, task_id: str, suff: str) -> str:
        """Upload image and return URL

        Args:
            path: Image file path
            task_id: Task ID
            suff: Calculated suffix

        Returns:
            URL of uploaded image
        """
        with open(path, 'rb') as f:
            files = {'file': f}
            data = {'taskId': task_id, 'suff': suff}

            print("Uploading...")
            response = requests.post(
                f"{self.endpoint}/api2/upload", files=files, data=data)
            response.raise_for_status()

            result = response.json()
            if not result.get("success"):
                print("Upload failed")
                sys.exit(1)

            return result.get("result", {}).get("url", "")

    def process_file(self, path: str) -> str:
        """Process single file upload

        Args:
            path: Image file path

        Returns:
            URL of uploaded image
        """
        # Check if file exists
        if not os.path.isfile(path):
            print(f"Error: File '{path}' does not exist")
            return ""

        try:
            # Get challenge
            challenge = self.get_challenge()

            # Use N value directly from server
            n_value = challenge["N"]

            print(
                f"Challenge received: Difficulty N={n_value} bits, IP={challenge['ip']}")

            # Calculate proof of work
            suff = self.find_suffix(
                challenge["pref"], n_value, challenge["taskId"])

            # Upload image
            print(f"Uploading image: {path}...")
            url = self.upload_image(path, challenge["taskId"], suff)

            print(f"Upload successful: {path}")
            return url

        except Exception as e:
            print(f"Error processing file '{path}': {str(e)}")
            return ""


def main():
    """Main function, parse command line arguments and execute upload process"""
    parser = argparse.ArgumentParser(
        description="Image uploader with proof of work mechanism")
    parser.add_argument("endpoint", help="API endpoint address")
    parser.add_argument("image_paths", nargs="+",
                        help="Image paths to upload, can specify multiple")

    args = parser.parse_args()

    # Create uploader instance
    uploader = ImageUploader(args.endpoint)

    # Process each image
    successful_uploads = 0
    upload_results = []

    for path in args.image_paths:
        print(f"\nProcessing file: {path}")
        url = uploader.process_file(path)
        if url:
            successful_uploads += 1
            upload_results.append((path, url))

    # Output statistics
    print(
        f"\nUpload complete: {successful_uploads}/{len(args.image_paths)} files successfully uploaded")

    # Output all upload links at the end
    if upload_results:
        print("Upload links:")
        for path, url in upload_results:
            print(url)


if __name__ == "__main__":
    main()
