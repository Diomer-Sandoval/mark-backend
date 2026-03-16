"""
MARK 2.0 Multi-Agent Chat System.

This package implements the 8 specialized agents from the MARK 2.0 architecture:
1. Onboarding & Context Agent
2. Competitor & Market Agent
3. Trends Agent
4. Platform Intelligence Agent
5. Strategy Agent (with Cialdini principles)
6. Content Creation Agent
7. Content Review Agent
8. Learning & Optimization Agent
"""

from .orchestrator import build_mark_agent
from .state import MARKAgentState

__all__ = ['build_mark_agent', 'MARKAgentState']
