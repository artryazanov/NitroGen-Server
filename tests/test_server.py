
import pytest
import json
import numpy as np
import sys
import os
from unittest.mock import MagicMock, mock_open, patch

# Add scripts directory to path to import serve.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts")))

from serve import handle_request, process_raw_image

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

# Note: We are not testing run_tcp_server and run_zmq_server directly here 
# because they involve infinite loops and socket bindings which are complex to unit test 
# without significant refactoring or complex threading mocks. 
# We focus on the logic handled by handle_request which covers the core business logic.

def test_process_raw_image_bmp():
    """Test BMP processing (flip + BGR2RGB)."""
    # Create a 256x256x3 image
    # Let's make it simple to check: Top-Left is Red, Bottom-Left is Blue
    # In BGR (BizHawk):
    # Top-Left (actually stored as last row in BMP) -> Blue (so when flipped it becomes Top)
    # But wait, BMP is Bottom-Up. So the first bytes in file are the Bottom row.
    # 
    # Let's just mock cv2 to ensure the calls are made correctly, 
    # OR we can trust the logic and just check if the output is transformed.
    # Given the complexity of dependencies, let's use a simple functional test.
    
    # Create a "raw" buffer that corresponds to a 256x256x3 array
    # Logic: process_raw_image calls cv2.flip(img, 0) and cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # We will mock cv2 in this test file to avoid depending on actual opencv installation if possible,
    # OR if we assume it's installed (which we do for the server), we can just run it.
    
    # Let's create a dummy input
    input_shape = (256, 256, 3)
    input_bytes = np.zeros(input_shape, dtype=np.uint8).tobytes()
    
    with patch('serve.cv2') as mock_cv2:
        # Mock returns
        mock_flipped = MagicMock()
        mock_converted = MagicMock()
        mock_cv2.flip.return_value = mock_flipped
        mock_cv2.cvtColor.return_value = mock_converted
        mock_cv2.COLOR_BGR2RGB = 4  # Constant
        
        # Test Default
        res_default = process_raw_image(input_bytes, image_source=None)
        assert res_default.shape == input_shape
        mock_cv2.flip.assert_not_called()
        
        # Test BMP
        res_bmp = process_raw_image(input_bytes, image_source="bmp")
        
        mock_cv2.flip.assert_called_once()
        mock_cv2.cvtColor.assert_called_once()
        # Verify call arguments
        # We can't easily check the numpy array arg equality with assert_called_with because of ambiguity
        # but we know it was called.
        assert res_bmp == mock_converted
