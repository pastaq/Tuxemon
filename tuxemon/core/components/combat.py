#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Tuxemon
# Copyright (C) 2014, William Edwards <shadowapex@gmail.com>,
#                     Benjamin Bean <superman2k5@gmail.com>
#
# This file is part of Tuxemon.
#
# Tuxemon is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Tuxemon is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Tuxemon.  If not, see <http://www.gnu.org/licenses/>.
#
# Contributor(s):
#
# William Edwards <shadowapex@gmail.com>
# Derek Clark <derekjohn.clark@gmail.com>
#
# core.components.combat
#

import logging

from core import prepare

logger = logging.getLogger(__name__)
class CombatEngine():
    """The CombatEngine class manages the matches and returns results of
    actions to the CombatRouter class.
    """
    def __init__(self, game):
        self.matches = {}
        self.game = game

    def update(self):
        for match in self.matches:
            match.update()

    def add_new_match(self, cuuid, params):
        self.matches[cuuid] = Match(params)
        print "self.matches", self.matches

    def route_combat(self, event, cuuid=None):
        if not cuuid:
            cuuid = self.game.combat_router.cuuid
        print cuuid, event
        if event["type"] == ["CLIENT_BATTLE_NEW"]:
            self.add_new_match(event["params"])


class Match():
    """The Match class executes as a single match between opponents.
    """
    def startup(self, params=None):
        self.players = params["players"]
        self.combat_type = params["combat_type"]         # Can be either "monster" or "trainer"

        self.current_players = {'player': {}, 'opponent': {}}
        # If we detected the players' health change, we need to animate it.
        self.current_players['player']['health_changed'] = False
        self.current_players['opponent']['health_changed'] = False
        # This is used to pause input from all players while actions are taking place.
        self.turn_in_progress = False
        self.status_check_in_progress = False   # Used to pause input during status check.
        self.status_check_completed = False

        # Keep track of the combat phases
        self.decision_phase = True     # The decision phase allows each player to select an action.
        self.action_phase = False      # The action phase resolves the actions that each player took.
        self.phase = "decision phase"  # The current state of combat.

    def update(self, time_delta):
        pass

    def start_decision_phase(self):
        """Once actions have been completed, this function will re-enable player input to allow the
        player to make a new decision.

        :param None:

        :rtype: None
        :returns: None

        """
        pass


    def start_action_phase(self):
        """After both players have input an action, this function will pause all player input and
        perform the selected actions of each player.

        :param None:

        :rtype: None
        :returns: None

        """
        pass

    def action_phase_update(self):
        """Updates the game every frame during the action phase.
        """
        pass


    def start_turn(self):
        """Starts a turn for a monster during the action phase.
        """
        pass

    def turn_update(self):
        """Updates every frame to carry out a monster's turn during the action phase.
        """
        pass

    def perform_action(self, player):
        """Perform an action that a single player has decided on. Players can decide to use a
        technique, item, switch monsters, or run away.

        :param player: The player object dictionary that is performing the action.

        :type player: Dictionary

        :rtype: None
        :returns: None
        """
        pass

    def status_check(self, player):
        """This method checks to see if a given player's currently active monster has any status
        effects (such as poison, paralyze, etc.) and resolves those effects. So if a monster was
        poisoned, executing this method will make that monster take poison damage. It also sets
        how much damage the monster took so we can animate their health going down in the update
        loop.

        :param player: The player object dictionary that we're checking the status for.

        :type player: Dictionary

        :rtype: None
        :returns: None
        """
        pass


# Import the android mixer if on the android platform
try:
    import pygame.mixer as mixer
except ImportError:
    import android.mixer as mixer

class CombatRouter():
    """The CombatRouter receives inputs from the local player and sends
    it to the local or network CombatEngine.
    """
    def __init__(self, game, combat_engine):
        self.game = game
        self.state = None
        self.combat_engine = combat_engine
        self.events = {"event2": "1"}
        self.responses = {}
        self.startup()
        self.cuuid = str(self.game.client.client.cuuid)
        self.game_type = ""

    def startup(self):
        if self.game.ishost or self.game.isclient:
            self.game_type = "NETWORK"
        else:
            self.route = self.combat_engine.route_combat
            self.game_type = "LOCAL"

        if not self.state:
            self.state = self.game.get_state_name("combat")

    def update(self):
        pass

    def route_combat(self, event_data):
        if self.game_type == "NETWORK:
            self.game.client.route_combat(event_data)

        elif self.game_type == "LOCAL":
            self.combat_engine.route_combat(event_data)

    def start_combat(self, params):
        # Add our players and setup combat
        self.game.push_state("COMBAT", params)

        # flash the screen
        self.game.push_state("FLASH_TRANSITION")

        # Start some music!
        logger.info("Playing battle music!")
        filename = "147066_pokemon.ogg"

        mixer.music.load(prepare.BASEDIR + "resources/music/" + filename)
        mixer.music.play(-1)
