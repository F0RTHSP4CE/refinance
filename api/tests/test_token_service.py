"""Tests for token service functionality"""

import json
from unittest.mock import Mock, patch

import pytest
from app.services.token import TokenService
from app.models.entity import Entity
from app.schemas.token import TokenSendReportSchema


class TestTokenService:
    """Test TokenService functionality"""

    def test_generate_and_send_new_token_telegram_inline_keyboard(self, test_app):
        """Test that Telegram messages are sent with inline keyboard buttons"""
        
        # Mock the entity service and config
        with patch('app.services.token.EntityService') as mock_entity_service, \
             patch('app.services.token.get_config') as mock_config, \
             patch('app.services.token.get_uow') as mock_uow, \
             patch('app.services.token.requests.post') as mock_post:
            
            # Setup config mock
            mock_config_instance = Mock()
            mock_config_instance.telegram_bot_api_token = "test_token"
            mock_config_instance.ui_url = "https://example.com"
            mock_config.return_value = mock_config_instance
            
            # Setup entity mock
            mock_entity = Mock()
            mock_entity.id = 123
            mock_entity.auth = {"telegram_id": 456789}
            
            # Setup entity service mock
            mock_entity_service_instance = Mock()
            mock_entity_service_instance.get.return_value = mock_entity
            mock_entity_service.return_value = mock_entity_service_instance
            
            # Setup requests.post mock
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            # Create token service instance
            token_service = TokenService(
                db=mock_uow.return_value,
                entity_service=mock_entity_service_instance,
                config=mock_config_instance
            )
            
            # Mock the _generate_new_token method to return a test token
            with patch.object(token_service, '_generate_new_token', return_value='test_token_123'):
                # Call the method
                result = token_service.generate_and_send_new_token(entity_id=123)
                
                # Verify the result
                assert result.entity_found is True
                assert result.token_generated is True
                assert result.message_sent is True
                
                # Verify requests.post was called with correct arguments
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                
                # Check the URL
                expected_url = "https://api.telegram.org/bot test_token/sendMessage"
                assert call_args[0][0] == expected_url
                
                # Check the data payload
                data = call_args[1]['data']
                assert data['chat_id'] == 456789
                assert data['text'] == "Click the button below to login"
                
                # Check the reply_markup contains inline keyboard
                reply_markup = json.loads(data['reply_markup'])
                assert 'inline_keyboard' in reply_markup
                assert len(reply_markup['inline_keyboard']) == 1
                assert len(reply_markup['inline_keyboard'][0]) == 1
                
                button = reply_markup['inline_keyboard'][0][0]
                assert button['text'] == "Login"
                assert button['url'] == "https://example.com/auth/token/test_token_123"
                
                # Check timeout
                assert call_args[1]['timeout'] == 5