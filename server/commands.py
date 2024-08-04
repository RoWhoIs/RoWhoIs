"""
RoWhoIs app command backend library
Pray to god nothing here breaks, soldier
"""

import logging


from utils import errors
from server import globals

logs = logging.getLogger(__name__)

cooldownValues = {
    "extreme": {"premium": 5, "standard": 2},
    "high": {"premium": 6, "standard": 3},
    "medium": {"premium": 7, "standard": 4},
    "low": {"premium": 8, "standard": 5},
}

# "Your enthusiasm is greatly appreciated, but please slow down! Try again in **{remaining_seconds}** second{'s' if remaining_seconds >= 2 else ''}.",
# "Hm.. Looks like we can't access this {context.lower()} right now. Please try again later."
# "{context} doesn't exist."
# "{context} is invalid."
# "RoWhoIs is experiencing unusually high demand and your command couldn't be fulfilled. Please try again later."
# "Whoops! An unknown error occurred. Please try again later."
