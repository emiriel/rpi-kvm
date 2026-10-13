#!/usr/bin/env python3
"""
Webhook receiver for automated deployment on git push.
Supports GitHub and Forgejo webhooks.
"""

import hashlib
import hmac
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', '')
PROJECT_PATH = os.environ.get('PROJECT_PATH', '/root/tools/rpi-kvm')
DEPLOY_SCRIPT = os.environ.get('DEPLOY_SCRIPT', '/root/tools/rpi-kvm/deployment/deploy.sh')
BRANCH = os.environ.get('DEPLOY_BRANCH', 'main')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('webhook-receiver')


def verify_signature_github(payload_body, signature_header):
    """Verify GitHub webhook signature."""
    if not WEBHOOK_SECRET:
        logger.warning("No WEBHOOK_SECRET set - skipping signature verification")
        return True

    if not signature_header:
        logger.error("No signature header provided")
        return False

    hash_algorithm, github_signature = signature_header.split('=')

    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, github_signature)


def verify_signature_forgejo(payload_body, signature_header):
    """Verify Forgejo webhook signature."""
    if not WEBHOOK_SECRET:
        logger.warning("No WEBHOOK_SECRET set - skipping signature verification")
        return True

    if not signature_header:
        logger.error("No signature header provided")
        return False

    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature_header)


def run_deployment():
    """Execute deployment script."""
    try:
        logger.info(f"Running deployment script: {DEPLOY_SCRIPT}")
        result = subprocess.run(
            [DEPLOY_SCRIPT],
            cwd=PROJECT_PATH,
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            logger.info(f"Deployment successful:\n{result.stdout}")
            return True, result.stdout
        else:
            logger.error(f"Deployment failed:\n{result.stderr}")
            return False, result.stderr

    except subprocess.TimeoutExpired:
        logger.error("Deployment timed out after 5 minutes")
        return False, "Deployment timeout"
    except Exception as e:
        logger.error(f"Deployment error: {e}")
        return False, str(e)


@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook."""

    # Detect webhook source
    if 'X-Hub-Signature-256' in request.headers:
        # GitHub webhook
        logger.info("Received GitHub webhook")
        signature = request.headers.get('X-Hub-Signature-256')
        if not verify_signature_github(request.data, signature):
            logger.error("Invalid GitHub signature")
            return jsonify({'error': 'Invalid signature'}), 401

        payload = request.json
        event = request.headers.get('X-GitHub-Event')

        if event != 'push':
            logger.info(f"Ignoring non-push event: {event}")
            return jsonify({'message': 'Ignored non-push event'}), 200

        ref = payload.get('ref', '')
        if not ref.endswith(f'/{BRANCH}'):
            logger.info(f"Ignoring push to non-target branch: {ref}")
            return jsonify({'message': f'Ignored push to {ref}'}), 200

    elif 'X-Forgejo-Signature' in request.headers:
        # Forgejo webhook
        logger.info("Received Forgejo webhook")
        signature = request.headers.get('X-Forgejo-Signature')
        if not verify_signature_forgejo(request.data, signature):
            logger.error("Invalid Forgejo signature")
            return jsonify({'error': 'Invalid signature'}), 401

        payload = request.json
        ref = payload.get('ref', '')
        if not ref.endswith(f'/{BRANCH}'):
            logger.info(f"Ignoring push to non-target branch: {ref}")
            return jsonify({'message': f'Ignored push to {ref}'}), 200

    elif 'X-Gitea-Signature' in request.headers:
        # Gitea webhook (Forgejo compatible)
        logger.info("Received Gitea webhook")
        signature = request.headers.get('X-Gitea-Signature')
        if not verify_signature_forgejo(request.data, signature):
            logger.error("Invalid Gitea signature")
            return jsonify({'error': 'Invalid signature'}), 401

        payload = request.json
        ref = payload.get('ref', '')
        if not ref.endswith(f'/{BRANCH}'):
            logger.info(f"Ignoring push to non-target branch: {ref}")
            return jsonify({'message': f'Ignored push to {ref}'}), 200
    else:
        logger.error("Unknown webhook source")
        return jsonify({'error': 'Unknown webhook source'}), 400

    # Execute deployment
    logger.info(f"Triggering deployment for {ref}")
    success, output = run_deployment()

    if success:
        return jsonify({
            'message': 'Deployment successful',
            'output': output
        }), 200
    else:
        return jsonify({
            'error': 'Deployment failed',
            'output': output
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'}), 200


if __name__ == '__main__':
    if not WEBHOOK_SECRET:
        logger.warning("WARNING: No WEBHOOK_SECRET set - webhook signatures will not be verified!")

    logger.info(f"Starting webhook receiver on port 9000")
    logger.info(f"Project path: {PROJECT_PATH}")
    logger.info(f"Deploy script: {DEPLOY_SCRIPT}")
    logger.info(f"Target branch: {BRANCH}")

    app.run(host='0.0.0.0', port=9000)
