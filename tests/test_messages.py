from unittest.mock import MagicMock


class TestMessages:
    def test_truncate_text_below_threshold(self):
        from ctxai.helpers.messages import truncate_text
        
        agent = MagicMock()
        agent.read_prompt.return_value = "[truncated]"
        
        result = truncate_text(agent, "short text", threshold=1000)
        assert result == "short text"

    def test_truncate_text_above_threshold(self):
        from ctxai.helpers.messages import truncate_text
        
        agent = MagicMock()
        agent.read_prompt.return_value = "[truncated]"
        
        text = "a" * 2000
        result = truncate_text(agent, text, threshold=1000)
        assert "[truncated]" in result
        assert len(result) == 1000

    def test_truncate_dict_by_ratio_string(self):
        from ctxai.helpers.messages import truncate_dict_by_ratio
        
        agent = MagicMock()
        
        result = truncate_dict_by_ratio(agent, "short", 1000, 500)
        assert result == "short"

    def test_truncate_dict_by_ratio_dict(self):
        from ctxai.helpers.messages import truncate_dict_by_ratio
        
        agent = MagicMock()
        agent.read_prompt.return_value = "[truncated]"
        
        data = {"key": "value"}
        result = truncate_dict_by_ratio(agent, data, 1000, 500)
        assert result == {"key": "value"}

    def test_truncate_dict_by_ratio_list(self):
        from ctxai.helpers.messages import truncate_dict_by_ratio
        
        agent = MagicMock()
        
        data = [1, 2, 3]
        result = truncate_dict_by_ratio(agent, data, 1000, 500)
        assert result == [1, 2, 3]
