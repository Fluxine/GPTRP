import csv
import io
import math
import aioconsole
from gptrp.character_sheet import CharacterSheet
from gptrp.agent import Action, ActionType, Agent
from pygptlink.gpt_context import GPTContext
from pygptlink.gpt_completion import GPTCompletion
from pygptlink.gpt_no_response_desired import GPTNoResponseDesired
from pygptlink.gpt_tools import GPTTools

_GM_MODEL = "gpt-4o"


class GameMaster(GPTTools):
    def __init__(self, completion: GPTCompletion,
                 pc_cs: CharacterSheet, all_npc_cs: list[CharacterSheet],
                 setting: str, start_hour: float) -> None:
        super().__init__()
        self.all_tools = self._describe_methods()
        self.context = GPTContext(model=_GM_MODEL, max_tokens=8000, max_response_tokens=700,
                                  persona_file="game_master_persona.txt", context_file="gm_context.jsonl")
        self.completion = completion

        self.hours_passed = start_hour
        self.setting = setting
        self.pc_cs = pc_cs
        self.npcs = {npc_cs.full_name: Agent(npc_cs) for npc_cs in all_npc_cs}

        self.tmp_observable_characters: list[str] = None

    async def advance_time(self, num_hours: int, num_minutes: int):
        """Advances the current time of day by a number of hours and minutes.

        This MUST be called AFTER having called perceive() for all characters to allow the characters to act.

        Args:
            num_hours (int): How many hours to advance time by.
            num_minutes (int): How many minutes to advance time by.
        """
        self.hours_passed += num_hours + num_minutes/60.0
        return GPTNoResponseDesired()

    def get_cs(self, full_name: str):
        if full_name == self.pc_cs.full_name:
            cs = self.pc_cs
        else:
            cs = self.npcs[full_name]

    async def update_character(self, full_name: str = None, description: str = None):
        """Updates the character sheet of a character.

        Args:
            full_name (str, optional): The full name of the character.
            description (str, optional): An in-depth description of the character including appearance, desires, values, goals, traits and possessions.
        """
        if not self.all_characters_valid([full_name]):
            return f"Error: No character by the name {full_name} exists."

        if full_name == self.pc_cs.full_name:
            cs = self.pc_cs
        else:
            cs = self.npcs[full_name]

        if full_name:
            cs.full_name = full_name
        if description:
            cs.description = description

    async def move_character(self, full_name: str, new_location: str):
        """Moves an existing character to a new location.

        Args:
            new_location (str): The current location of the character, free form text. E.g. "in the neighbouring town" or "in the upstairs bedroom".
        """
        if full_name == self.pc_cs.full_name:
            self.pc_cs.location = new_location
        else:
            npc = self.npcs.get(full_name, None)
            if not npc:
                return "ERROR: No character by the name {full_name} exists"
            npc.cs.location = new_location

    async def perceive(self, character: str, observation: str):
        """Informs the given character about what they perceive. May only be called once per round per character.
        The character must be one that already exists. Using a character name that have not been expressly mentioned already WILL result in an error.

        Args:
            character (str): The full name of an already existing character.
            observation (str): A detailed description of what they perceived with their sight, smell, touch and hearing.
        """
        if character in self.pc_cs.full_name:
            print(f"The game master says: {observation}")
        else:
            npc = self.npcs.get(character, None)
            if npc:
                npc.experience(observation)
            else:
                return f"Error: No character by the name: {character} exists! You may not invent new characters!"

    def all_characters_valid(self, characters: list[str]):
        for c in characters:
            if not (c == self.pc_cs.full_name) and not (c in self.npcs.keys()):
                return False
        return True

    def time(self):
        tod = self.hours_passed % 24
        fraction, hours = math.modf(tod)
        minutes = round(60*fraction)
        return f"{round(hours):02}:{minutes:02} (24h clock)"

    def day(self):
        return f"{math.floor(self.hours_passed/24)}"

    def all_character_sheets(self):
        cs: list[CharacterSheet] = []
        cs.append(self.pc_cs)
        cs.extend([npc.cs for npc in self.npcs.values()])
        cs.sort(key=lambda x: x.full_name)
        return "\n".join([x.render() for x in cs])

    def decide_turn_order(self) -> list[str]:
        # This function must make sure that all character names are correctly spelt
        ans = [self.pc_cs.full_name]
        ans.extend(npc for npc in self.npcs.keys())
        return ans

    async def do_player_input(self, preliminary_actions: str, time_of_day: str, day: str) -> list[Action]:
        print(
            f"""It is your turn to act. The current time is {time_of_day} on day {day} of the adventure.

Your character sheet:
{self.pc_cs.render()}
""")
        if preliminary_actions:
            print(preliminary_actions)
        query = ""
        while not query or query not in "aAsSpP":
            query = await aioconsole.ainput("Pass (P), Action (A) or Speech (S)? ")

        actions: list[Action] = []
        if query in "aA":
            actions.append(Action(self.pc_cs.full_name, ActionType.PERFORM_ACTION, await aioconsole.ainput("What action do you take? ")))
            words = await aioconsole.ainput("What do you say? ")
            if words:
                actions.append(
                    Action(self.pc_cs.full_name, ActionType.SPEAK, words))
        elif query in "sS":
            actions.append(Action(self.pc_cs.full_name, ActionType.SPEAK, await aioconsole.ainput("What do you say? ")))
            acts = await aioconsole.ainput("What action do you take? ")
            if acts:
                actions.append(Action(self.pc_cs.full_name,
                               ActionType.PERFORM_ACTION, acts))
        return actions

    def fmt_p_actions(self, p_actions: list[Action]):
        return "\n---\n".join([x.render() for x in p_actions])

    def sticky_prompt(self):
        return f"""The current time is {self.time()}
Days passed since start: {math.floor(self.hours_passed / 24)}.

The backstory is: {self.setting}

All characters and their sheets are listed below:
{self.all_character_sheets()}"""

    async def do_perceive(self):
        prompt = f"""A new round is about to start, use perceive() exactly once per character to tell them what they perceive of the events from the previous round.

Keep in mind:
 - Do not disclose names of characters that haven't been introduced met.
 - The environment and relative position of characters can influence what they perceive of each other.
 - The observations should focus on setting the mood, location, situation etc.
 - Each characters must be provided a unique and tailored message.
 - Any words spoken that could be heard MUST be included verbatim, with the speaker indicated.
 - Actions taken must be described unmodified to the perceiver if they can see or hear them, with the actor indicated.

Immediately after you have called perceive() exactly once for each character, you MUST call advance_time() to allow the characters to act."""
        c = self.context.copy()
        c.append_system_message(prompt)
        await self.completion.complete(
            context=c, gpt_tools=self.all_tools, force_tool=['perceive', 'advance_time'], extra_system_prompt=self.sticky_prompt())

    async def do_partial_observations(self, character: str, p_actions: list[Action]):
        observable_actions_prompt = f"""It is {character}'s turn to act, based on the preliminary actions of other characters listed below, tell {character} what if anything they perceive of these actions.

Keep in mind:
- Some actions might not be perceived at all, in which case they should not be divulged.
- Some actions might only be partially perceived, in which case divulge them with modification.
- Do not disclose the names of characters that are not yet known to {character}. If unsure, assume unfamiliarity.
- Do not motivate your thoughts as that would give away information that {character} doesn't know yet.

Take into account things like:
- Obstructions and distance to the current position of the action.
- Sensory restrictions surrounding noise levels, and whether {character} is deeply focused and might not notice.
- The current state of the character doing the action
- Other similar factors that might result in the preliminary actions not being noticed by {character}.

If {character} perceives none of the actions below, say only "None".

{self.fmt_p_actions(p_actions)}"""
        c = self.context.copy()
        c.append_system_message(observable_actions_prompt)
        observable_actions_str = await self.completion.complete(context=c, extra_system_prompt=self.sticky_prompt())
        if observable_actions_str and observable_actions_str.casefold() == "none".casefold():
            observable_actions_str = None

    async def do_adventure_init(self):
        # First round, GM does introductions.
        prompt = f"""This is the start of the adventure.

Give a summary of the initial environment and situation, as well as where each character is and their current condition, and whether anything noticeable has happened or not."""
        self.context.append_system_message(prompt)
        await self.completion.complete(
            context=self.context, extra_system_prompt=self.sticky_prompt())
        await self.do_perceive()

    async def do_round(self):
        if not self.context.context:
            await self.do_adventure_init()

        p_actions: list[Action] = []
        character_order = self.decide_turn_order()
        for character in character_order:
            observable_actions_str = None
            if character != character_order[0]:
                observable_actions_str = await self.do_partial_observations(character, p_actions)

            if character == self.pc_cs.full_name:
                p_actions.extend(await self.do_player_input(preliminary_actions=observable_actions_str, time_of_day=self.time(),
                                                            day=self.day()))
            else:
                npc = self.npcs.get(character, None)
                p_actions.extend(await npc.do_turn(completion=self.completion,
                                                   observable_actions=observable_actions_str,
                                                   time_of_day=self.time(),
                                                   day=self.day()))

        # Force the model to generate a "world observable state" first in its own context, it should then be better able to
        # maintain consistency for the other character's individual observations
        all_actions_formatted = self.fmt_p_actions(p_actions)
        prompt = f"""All the active characters have declared their desired actions and things to say for this round based on the their turn order, and they are as follows:

{all_actions_formatted}

Keep in mind:
 - Resolve any conflicting actions, reactions and interruptions to determine the final turn of events for this round from the all-seeing game masters point of view.
 - You must update the position of each character that moved with move_character().
 - If a character's description has changed, you must update it using update_character().
 - You must include everything that was said verbatim and by whom in this summary/resolution of actions.
 
Upon resolving all actions, this round is considered ended.

The current time is {self.time()}
Days passed since start: {self.day()}."""
        self.context.append_system_message(prompt)
        await self.completion.complete(context=self.context, extra_system_prompt=self.sticky_prompt(), gpt_tools=self._describe_methods(), allowed_tools=['move_character', 'update_character'])

        # Now the model needs to tell everyone what they observed, this is the ground truth.
        await self.do_perceive()
