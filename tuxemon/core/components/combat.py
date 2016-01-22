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
import uuid
from core import prepare

logger = logging.getLogger(__name__)
class CombatEngine():
    """The CombatEngine class manages the matches and returns results of
    actions to the local EventRouter or networked client.
    """
    def __init__(self, game):
        self.matches = {}
        self.game = game

    def set_type(self):
        try:
            self.notify_route = self.game.event_router.handle_response
            self.engine_type = "CLIENT"
        except AttributeError:
            self.notify_route = self.game.handle_combat_response
            self.engine_type = "SERVER"
        logger.info("Combat engine started as", self.engine_type)

    def update(self):
        for match in self.matches:
            match.update()

    def add_new_match(self, cuuid, params):
        self.matches[cuuid] = Match(params)

    def route_combat(self, event, cuuid=None):
        if not cuuid:
            self.cuuid = str(self.game.client.client.cuuid)

        if event["type"] == "CLIENT_BATTLE_NEW":
            self.add_new_match(cuuid, event["params"])
            event_data={"type":"NOTIFY_CLIENT_BATTLE_NEW",
                        "params": event["params"]}
            self.notify_route(cuuid, event_data)

class Match():
    """The Match class executes as a single match between opponents.
    """
    def __init__(self, params):
        self.players = params["players"]
        self.combat_type = params["combat_type"]         # Can be either "monster" or "trainer"

        # This is used to pause input from all players while actions are taking place.
        self.turn_in_progress = False
        self.status_check_in_progress = False   # Used to pause input during status check.
        self.status_check_completed = False

        # Keep track of the combat phases
        self.decision_phase = True     # The decision phase allows each player to select an action.
        self.action_phase = False      # The action phase resolves the actions that each player took.

        self.phase = "decision phase"  # The current state of combat.

        def set_xp(players):
            for player in players:
                mons = player.monsters[0]
                # Leveling is based off of total experience, so we need to do a bit of calculation
                # to get the percentage of experience needed for the current level.
                player.zero_xp = mons.experience_required_modifier * mons.level ** 3
                player.full_xp = mons.experience_required_modifier * (mons.level + 1) ** 3
                player.level_xp = mons.total_experience - player.zero_xp
                player.max_xp = player.full_xp - player.zero_xp
                player.current_xp = player.level_xp / float(player.max_xp)
                logger.info("Current XP: %s / %s" % (player.level_xp, player.max_xp))
                player.monster_last_hp = mons.current_hp

        print self.players
        set_xp(self.players)
        print self.players

    def startup(self, params=None):
        pass

    def update(self, time_delta):
        print(time_delta)
        player1_dict =  self.current_players['player1']
        player2_dict =  self.current_players['player2']

        # If a player has an AI associated with it, execute that AI's decision
        # function

        if player1_dict['player'].ai and not player1_dict['action']:
            player1_dict['action'] = player1_dict['player'].ai.make_decision(
                player1_dict,
                player2_dict)

        if player2_dict['player'].ai and not player2_dict['action']:
            player2_dict['action'] = player2_dict['player'].ai.make_decision(
                player2_dict,
                player1_dict)

        # If both players have selected an action, start the action phase.
        if player1_dict['action'] and player2_dict['action']:
            self.start_action_phase()

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

        # This will be executed when both players have selected an action.
        self.action_phase = True
        self.decision_phase = False
        self.phase = "action phase"
        players = self.current_players

        # Create a list of players ordered by who will go first.
        self.turn_order = []

        # Determine which monster goes first based on the speed of the monsters.
        if players['player1']['monster'].speed >= players['player2']['monster'].speed:
            self.turn_order.append(players['player1'])
            self.turn_order.append(players['player2'])
        else:
            self.turn_order.append(players['player2'])
            self.turn_order.append(players['player1'])

    def action_phase_update(self):
        """Updates the game every frame during the action phase.
        """
        # If we're in the action phase, but an action is not actively being carried out, start
        # the next player's action.
        if not self.turn_in_progress:
            self.start_turn()

        # If an action IS actively being carried out, draw the animations for the action.
        else:
            self.turn_update()

        # If all turns have been taken, start the decision phase.
        if len(self.turn_order) == 0:
            self.start_decision_phase()

    def start_turn(self):
        """Starts a turn for a monster during the action phase.
        """
        logger.info("")
        logger.info("Starting turn for " + self.turn_order[0]['player'].name)
        if not self.status_check_in_progress and not self.status_check_completed:
            logger.info("  Performing status check and resolving damage from status.")
            self.status_check(self.turn_order[0])
            self.status_check_in_progress = True
            self.status_check_completed = False
            self.phase = "status check in progress"

        # We want to perform our action AFTER the status check has completed.
        elif self.status_check_completed:
            logger.info("  Status check completed. Performing action.")
            self.perform_action(self.turn_order[0])
            self.status_check_in_progress = False
            self.status_check_completed = False

        self.turn_in_progress = True

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


class EventRouter():
    """The EventRouter receives inputs from the local player and sends
    it to the local or network CombatEngine.
    """
    def __init__(self, game):
        self.game = game
        self.state = None
        self.events = {}
        self.responses = {}
        self.startup()
        self.cuuid = str(self.game.client.client.cuuid)
        self.game_type = ""

        # Import the android mixer if on the android platform
        try:
            import pygame.mixer as mixer
        except ImportError:
            import android.mixer as mixer
        self.mixer = mixer

    def startup(self):
        if self.game.ishost or self.game.isclient:
            self.game_type = "NETWORK"
        else:
            self.combat_route = self.game.combat_engine.route_combat
            self.game_type = "LOCAL"

        if not self.state:
            self.state = self.game.get_state_name("combat")

    def update(self):
        for euuid in self.events:
            event_data = self.events[euuid]
            self.combat_route(event_data)
            del self.events[euuid]
            return

        for euuid in self.responses:
            cuuid = self.responses[euuid]["cuuid"]
            event_data = self.responses[euuid]["event_data"]
            self.handle_response(cuuid, event_data)
            del self.responses[euuid]
            return

    def add_event(self, event_data):
        euuid = str(uuid.uuid1())
        self.events[euuid] = event_data

    def start_combat(self, params):
        # Add our players and setup combat
        self.game.push_state("COMBAT", params)

        # flash the screen
        self.game.push_state("FLASH_TRANSITION")

        # Start some music!
        logger.info("Playing battle music!")
        filename = "147066_pokemon.ogg"

        self.mixer.music.load(prepare.BASEDIR + "resources/music/" + filename)
        self.mixer.music.play(-1)

    def handle_response(self, cuuid, event_data):
        if event_data["type"] == "NOTIFY_CLIENT_BATTLE_NEW":
            self.start_combat(event_data["params"])
