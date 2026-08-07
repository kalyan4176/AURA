import pytest
from app.application.budget.services import ai_budget_manager


def test_deterministic_routing_heuristics():
    # Test query strings that can be resolved deterministically
    assert ai_budget_manager.is_deterministic("What is the average age of respondents?") is True
    assert ai_budget_manager.is_deterministic("Find how many missing values are in the email column") is True
    assert ai_budget_manager.is_deterministic("Calculate the standard deviation of salary") is True
    assert ai_budget_manager.is_deterministic("Are there duplicate records in this workspace?") is True
    
    # Test queries requiring semantic explanations
    assert ai_budget_manager.is_deterministic("Draft an executive summary of our Q3 growth report") is False
    assert ai_budget_manager.is_deterministic("What are your recommendations for improving user activation rates?") is False
