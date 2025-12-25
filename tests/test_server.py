
import pytest
import json
import numpy as np
import sys
import os
from unittest.mock import MagicMock, mock_open, patch

# Add scripts directory to path to import serve.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts")))

from serve import handle_request

def test_handle_request_reset():
    """Test handling of reset request."""
    session = MagicMock()
    request = {"type": "reset"}
    
    response = handle_request(session, request)
    
    session.reset.assert_called_once()
    assert response["status"] == "ok"

def test_handle_request_info():
    """Test handling of info request."""
    session = MagicMock()
    session.info.return_value = {"foo": "bar"}
    request = {"type": "info"}
    
    response = handle_request(session, request)
    
    assert response["status"] == "ok"
    assert response["info"] == {"foo": "bar"}

def test_handle_request_predict(mock_model):
    """Test handling of predict request."""
    session = MagicMock()
    # Mock predict return
    session.predict.return_value = {"buttons": np.array([1]), "j_left": np.array([0]), "j_right": np.array([0])}
    
    request = {"type": "predict"}
    raw_image = np.zeros((256, 256, 3), dtype=np.uint8)
    
    response = handle_request(session, request, raw_image=raw_image)
    
    session.predict.assert_called_once_with(raw_image)
    assert response["status"] == "ok"
    assert "pred" in response

def test_handle_request_unknown():
    """Test handling of unknown request type."""
    session = MagicMock()
    request = {"type": "unknown_type"}
    
    response = handle_request(session, request)
    
    assert response["status"] == "error"
    assert "Unknown type" in response["message"]

