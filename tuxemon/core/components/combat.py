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

from collections import namedtuple

from core.components.event.actions.combat import Combat

logger = logging.getLogger(__name__)
logger.debug("components.combat successfully imported")

class CombatEngine():
    """The CombatEngine class manages the matches and returns results of
    actions to the local EventRouter or networked client.
    """
    def __init__(self, server):
        self.matches = {}
        self.server = server
        self.combat = Combat()

    def update(self):
        for match in self.matches.keys():
            current_match = self.matches[match]
            if current_match.combat_over:
                winner = current_match.winner
                loser = current_match.loser
                logger.info("Match over. Winner: " + str(winner) + " Loser: " + str(loser))
                del self.matches[match]
            else:
                current_match.update()

    def route_combat(self, cuuid, event_data):
        if event_data["type"] == "CLIENT_BATTLE_NEW":
            if cuuid  not in self.matches:
                self.add_new_match(cuuid, event_data)

    def add_new_match(self, cuuid, event_data):
        params = None
        Action = namedtuple("action", ["type", "parameters"])
        action = Action(event_data["action"][0], event_data["action"][1])
        if event_data["combat_type"] == "monster":

            params = self.combat.s_rand_encounter(self.server,
                                                  cuuid,
                                                  action
                                                  )

        if params:
            self.matches[cuuid] = Match(params)
        else:
            return False


class Match():
    """The Match class executes as a single match between opponents.
    """
    def __init__(self, params):
        logger.debug("NEW MATCH!")
        self.players = params["players"]
        self.combat_type = params["combat_type"]  # Can be "duel", "monster", or "trainer"

        self.current_players = {'player1': {}, 'player2': {}}

        # If we detected the players' health change, we need to animate it.
        self.current_players['player1']['health_changed'] = False
        self.current_players['player2']['health_changed'] = False

        # This is used to pause input from all players while actions are taking place.
        self.turn_in_progress = False
        self.status_check_in_progress = False   # Used to pause input during status check.
        self.status_check_completed = False

        # Keep track of the combat phases
        self.combat_over = False
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

        set_xp(self.players)

        # Loop through all of our players and set up our monster.
        for player_name, player_dict in self.current_players.items():
            if player_name == 'player1':
                player_dict['player'] = self.players[0]

            elif player_name == 'player2':
                player_dict['player'] = self.players[1]

            # Get the player's monster object
            player_dict['monster'] = player_dict['player'].monsters[0]

            # Set the action that the player has decided to do this turn. For example, this
            # action will be set if the player decides to use a move or an item, etc.
            player_dict['action'] = None

            # The "monster_last_hp" is used to detect if damage has been done this frame.
            player_dict['monster_last_hp'] = player_dict['monster'].current_hp
            print("player_dict", player_dict)

    def startup(self, params=None):
        pass

    def update(self):
        if self.combat_over:
            return False

        logger.debug("Update")
        player1_dict = self.current_players['player1']
        player1_dict['player'] = self.players[0]
        player1_dict['monster'] = player1_dict['player'].monsters[0]

        player2_dict = self.current_players['player2']
        player2_dict['player'] = self.players[1]
        player2_dict['monster'] = player2_dict['player'].monsters[0]

        # If a player has an AI associated with it, execute that AI's decision
        # function
        if self.phase == "decision phase":
            if player1_dict['player'].ai and not player1_dict['action']:
                player1_dict['action'] = player1_dict['player'].ai.make_decision(
                    player1_dict, player2_dict)
                logger.debug("AI determined to use " + str(player1_dict['action']))

            if player2_dict['player'].ai and not player2_dict['action']:
                player2_dict['action'] = player2_dict['player'].ai.make_decision(
                    player2_dict, player1_dict)
                logger.debug("AI Determined to use " +str(player2_dict['action']))

        # If both players have selected an action, start the action phase.
        if player1_dict['action'] and player2_dict['action']:
            self.start_action_phase()

        # Handle things that take place during the action phase like health going down, etc.
        if self.action_phase:
            self.action_phase_update()

    def start_decision_phase(self):
        """Once actions have been completed, this function will re-enable player input to allow the
        player to make a new decision.

        :param None:

        :rtype: None
        :returns: None

        """
        logger.debug("Decision phase")

        # End the action phase and start the decision phase.
        self.action_phase = False
        self.decision_phase = True
        self.phase = "decision phase"

    def start_action_phase(self):
        """After both players have input an action, this function will pause all player input and
        perform the selected actions of each player.

        :param None:

        :rtype: None
        :returns: None

        """
        logger.debug("Action Phase")
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
        logger.debug("Turn order for this phase is as follows: " + str(self.turn_order))

    def action_phase_update(self):
        """Updates the server every frame during the action phase.
        """
        # If we're in the action phase, but an action is not actively being carried out, start
        # the next player's action.
        logger.debug("Action Phase Update")
        if not self.turn_in_progress:
            logger.debug("Starting Turn")
            self.start_turn()

        # If an action IS actively being carried out, draw the animations for the action.
        else:
            logger.debug("Updating Turn")
            self.turn_update()

        # If all turns have been taken, start the decision phase.
        if len(self.turn_order) == 0:
            logger.debug("All turns complete, starting decision phase")
            self.start_decision_phase()

    def start_turn(self):
        """Starts a turn for a monster during the action phase.
        """
        logger.info("Starting turn for " + self.turn_order[0]['player'].name)
        if not self.status_check_in_progress and not self.status_check_completed:
            logger.info("  Performing status check and resolving damage from status.")
            print self.turn_order[0]
            print self.turn_order[1]
            self.status_check(self.turn_order[0])
            self.status_check_in_progress = True
            self.status_check_completed = False
            self.phase = "status check in progress"

        # We want to perform our action AFTER the status check has completed.
        elif self.status_check_completed:
            logger.info("  Status check completed. Performing action.")
            player = self.turn_order[0]
            for player_name in self.current_players:
                if self.current_players[player_name] == player:
                    continue
                else:
                    opponent = self.current_players[player_name]
                    print opponent

#            self.turn_order.append(players['player1'])
            self.perform_action(player, opponent)
            self.status_check_in_progress = False
            self.status_check_completed = False

        self.turn_in_progress = True
        logger.debug("Turn currently in progress")

    def turn_update(self):
        """Updates every frame to resolve the end of a turn during the action phase.
        """
        logger.debug("Turn Update")

        players = self.current_players

        # If a monster has taken damage this frame, then start animating the health.
        for player_name, player in players.items():
            for plyr_nm, plyr in players.items():
                if plyr == player: continue
                else:
                    other_player = plyr
                    op_nm = plyr_nm
            if player['monster_last_hp'] != player['monster'].current_hp:
                logger.info("Player Health Change: " + str(player['monster_last_hp']) +
                    " -> " + str(player['monster'].current_hp))

                players[player_name]['starting_health'] = player['monster_last_hp']
                players[player_name]['target_health'] = player['monster'].current_hp

                # Indicate that this monster's health has changed and in which direction it has been changed. Was
                # the monster damaged or healed?
            if player['monster_last_hp'] < player['monster'].current_hp:
                players[player_name]['health_changed'] = True
                logger.debug("<%s's> monster's health has gone up" % player_name)
            elif player['monster_last_hp'] > player['monster'].current_hp:
                players[player_name]['health_changed'] = True
                logger.debug("<%s's> monster's health has gone down" % player_name)
            else:
                players[player_name]['health_changed'] = False
                logger.debug("<%s's> monster's health has not changed" % player_name)

            # Set the last HP value to the current one so we don't execute this function endlessly
            players[player_name]['monster_last_hp'] = player['monster'].current_hp
            players[op_nm]['monster_last_hp'] = other_player['monster'].current_hp

            # If the monster is fainting, remove the monster and handle
            # completing the turn.
            if player['monster'].state == "fainting" and not player['health_changed']:
                players[player_name]['monster'].state = "fainted"
                logger.debug("<%s's> moster has fainted" % player_name)
                # Aliases to make referencing monsters more concise
                mons1 = players[player_name]['monster']
                mons2 = players[op_nm]['monster']

                # Give player's monster experience for faint of opponent monster
                xp = (mons1.experience_give_modifier * mons1.level) ** 3
                mons2.give_experience(xp)
                logger.info("<%s's> Monster gained experience: %i" % (player_name, xp))

                # Check to see if the player has any more remaining monsters in their
                # party that haven't fainted.
                alive_monster_found = False
                for monster in players[player_name]['player'].monsters:
                    if monster.status != "FNT":
                        alive_monster_found = True

                if alive_monster_found:
                    logger.warning("Let the player choose his next monster!")

                else:
                        logger.info("<%s> has won the match." % other_player)
                        self.phase = "battle_over"
                        self.winner = other_player
                        self.loser = player_name

            ########################################################
            #                  Creature Capturing                  #
            ########################################################
            # Needs rework to be player agnostic
            if "capturing" in self.phase:

                if self.phase == "capturing success":
                    logger.info("Capturing %s!!!" % players[other_player]['monster'].name)
                    self.phase = "captured"
                elif self.phase == "capturing fail":
                    logger.info("Could not capture %s!" % players[other_player]['monster'].name)
                    self.phase = "action phase"

            # Handle when the battle is over
            if self.phase == "battle_over" or self.phase == "captured":
                logger.debug("The battle is over. Ending combat.")
                self.combat_over = True


            #######################################################
            #                   Finish turn                       #
            #######################################################

            # Stop this turn once the health animations have stopped and the appropriate amount
            # of time has passed for the info menu.
            if (not players[player_name]['health_changed']
                and not players[op_nm]['health_changed']
                and (players[player_name]['monster'].state != "fainting" \
                     or players[op_nm]['monster'].state != "fainting")):
                self.turn_in_progress = False

            if self.status_check_in_progress:
                self.status_check_completed = True
                self.phase = "status check completed"

            # If this isn't part of a status check, end the turn for the current player.
            else:
                self.turn_order.pop(0)      # Remove the player from the turn list.
                logger.debug("<%s's> turn is over" % player_name)

    def perform_action(self, player, target):
        """Perform an action that a single player has decided on. Players can decide to use a
        technique, item, switch monsters, or run away.

        :param player: The player object dictionary that is performing the action.

        :type player: Dictionary

        :rtype: None
        :returns: None
        """
        logger.debug("Perform Action")
        print player
        # If the player selected a technique, use the selected technique on the opposing monster.
        if 'technique' in player['action']:

            # Get the monster's last hp value before the damage is done
            player['monster_last_hp'] = player['monster'].current_hp

            # Get the move that the player decided to use.
            selected_move = player['action']['technique']
            player['monster'].moves[selected_move].use(
                user=player['monster'], target=target['monster'])

            logger.info("Using " + player['monster'].moves[selected_move].name)
            logger.info("Level: " + str(player['monster'].level))
            logger.info("")
            logger.info("Player monster HP: " + str(player['monster'].current_hp))
            logger.info("Opponent monster HP: " + str(target['monster'].current_hp))

            # If using this technique kills either the player's monster OR the opponent's
            # monster, set their status to FUCKING DEAD.
            if target['monster'].current_hp <= 0:
                target['monster'].current_hp = 0
                target['monster'].status = 'FNT'
                target['monster'].state = "fainting"

            if player['monster'].current_hp <= 0:
                player['monster'].current_hp = 0
                player['monster'].status = 'FNT'
                player['monster'].state = "fainting"

        # If the player selected to use an item, use the item.
        elif 'item' in player['action']:

            # Get the monster's last hp value before the item is used, so we can animate
            # their health in the main update loop.
            player['monster_last_hp'] = player['monster'].current_hp
            player['opponent']['monster_last_hp'] = player['opponent']['monster'].current_hp

            # Get the item object from the player's inventory that the player decided to use
            # and USE IT.
            item_name = player['action']['item']['name']
            item_target = player['action']['item']['target']
            item_to_use = player['player'].inventory[item_name]['item']

            # Use item and change game state if captured or not
            if "capture" in item_to_use.effect:
                if item_to_use.capture(item_target, game):
                    self.phase = "capturing success"
                else:
                    self.phase = "capturing fail"
            else:
                item_to_use.use(item_target, game)

            logger.info("Using item!")

        # Remove the player's current decision in preparation for the next turn.
        player['action'] = None

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
        logger.debug("Status Check")

        logger.info('Checking Status for ' + player['player'].name)
        logger.info('  Monster Status: ' + player['monster'].status)

        # Get the monster's hp before resolving damage from status effects.
        player['monster_last_hp'] = player['monster'].current_hp

        # If the player's monster was poisoned, make the monster take poison damage.
        if player['monster'].status == 'Poisoned':

            # Only take poison damage if we've been poisoned for longer than 1 turn.
            if player['monster'].status_turn >= 1:
                logger.info("  This monster is taking poison damage this turn.")
                self.info_menu.text = "%s took poison damage!" % player['monster'].name
                self.info_menu.elapsed_time = 0.0
                player['monster_last_hp'] = player['monster'].current_hp
                player['monster'].current_hp -= 10

            # Keep track of how many turns this monster has been poisoned.
            player['monster'].status_turn += 1

        # If the player's HP drops below zero due to status effects, set them fainting.
        # Then we can animate the monster fainting based on this variable.
        if player['monster'].current_hp <= 0:
            player['monster'].status = 'FNT'
            player['monster'].state = "fainting"

