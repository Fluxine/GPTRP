from enum import Enum, auto
import os
from gptrp.character_sheet import CharacterSheet
from pygptlink.gpt_context import GPTContext
from pygptlink.gpt_completion import GPTCompletion
from pygptlink.gpt_no_response_desired import GPTNoResponseDesired
from pygptlink.gpt_tools import GPTTools

from gptrp.reverse_index import FuzzyReverseIndex

_AGENT_MODEL = "gpt-4o"


class ActionType(Enum):
    SPEAK = auto()
    PERFORM_ACTION = auto()


class Action:
    def __init__(self, character: str, action_type: ActionType, description: str) -> None:
        self.character = character
        self.type = action_type
        self.description = description

    def render(self):
        if self.type == ActionType.SPEAK:
            return f"{self.character} says: {self.description}"
        return f"{self.character} takes the following action: {self.description}"


class Agent(GPTTools):
    """An agent uses a GPT model to generate actions taken by an NPC during a role playing session.

    Each agent represents exactly one NPC.
    """

    def __init__(self, character_sheet: CharacterSheet, agent_dir: str = None) -> None:
        super().__init__()
        if not agent_dir:
            agent_dir = os.path.join("agents", character_sheet.full_name)

        context_file = os.path.join(
            agent_dir, character_sheet.full_name+".jsonl")

        self.cs = character_sheet
        self.context = GPTContext(model=_AGENT_MODEL, max_response_tokens=1500, max_tokens=15000,
                                  persona_file="npc_persona.txt", context_file=context_file)
        self.actions: list[Action] = []
        self.memories = FuzzyReverseIndex(
            filepath=os.path.join(agent_dir, "memories.jsonl"))

        self.turn_actions: set[str] = set()

    async def speak(self, message: str):
        """Speak as your character. Other players nearby will hear what you say unless you whisper.

        May only be called at most once per turn.

        Args:
            message (str): Exact message to be spoken.
        """
        _ACTION_NAME = "speak"
        if _ACTION_NAME in self.turn_actions:
            return f"Error: Only one {_ACTION_NAME} call per turn allowed."
        self.turn_actions.add(_ACTION_NAME)
        self.actions.append(
            Action(self.cs.full_name, ActionType.SPEAK, message))

    async def make_note(self, keywords: str, note: str):
        """Create a permanent note about something you wish to remember long term. The notes are
        later searchable by you by keyword using `search_notes`. Your notes are guaranteed to be
        private to yourself.

        May only be called at most once per turn.

        Args:
            keywords (str): Comma separated list of keywords this note should be searchable by.
            note (str): Free form text with the contents of the note.
        """
        _ACTION_NAME = "make_note"
        if _ACTION_NAME in self.turn_actions:
            return f"Error: Only one {_ACTION_NAME} call per turn allowed."

        self.turn_actions.add(_ACTION_NAME)
        keys = [v.rstrip() for v in keywords.split(",")]
        self.memories.index_document(keys=keys, value=note)

    async def search_notes(self, keywords: str):
        """Keyword search through all previously made notes.

        Args:
            keywords (str): Comma-separated keywords for topic retrieval.
        """
        keys = [v.rstrip() for v in keywords.split(",")]
        topics = self.memories.query(search_terms=keys)
        return "\n\n".join(topics)

    async def perform_action(self, description: str):
        """Attempt to perform an action in the world as your character. The outcome will be decided by the GameMaster.

        May only be called at most once per turn.

        Args:
            description (str): Detailed description of the action, including targets, preconditions, effects, or other relevant information.
        """
        _ACTION_NAME = "perform_action"
        if _ACTION_NAME in self.turn_actions:
            return f"Error: Only one {_ACTION_NAME} call per turn allowed."
        self.turn_actions.add(_ACTION_NAME)
        self.actions.append(
            Action(self.cs.full_name, ActionType.PERFORM_ACTION, description))

    async def end_turn(self):
        """Ends your turn."""
        return GPTNoResponseDesired()

    def experience(self, experience: str):
        """The game master informs the agent of something that is observable to the agent.

        #NO_GPT_TOOL

        Args:
            experience (str): a text description of what the agent observed.
        """
        self.context.append_user_prompt(user="GameMaster", content=experience)

    async def do_turn(self, completion: GPTCompletion, observable_actions: str, time_of_day: str, day: str) -> list[Action]:
        """The agent takes its turn and performs any actions it wants to take.

        #NO_GPT_TOOL

        args:
            completion (GPTCompletion): A completion object used by the agent to perform its turn.

        returns:
            Only actions that are observable by the game master are returned as a temporally ordered list of Actions.
            The return can be the empty list if no action observable by the game master.
        """

        # I think that either this should remain in the context, or the actions taken
        # should be removed from the context to keep actions taken in response to this
        # prompt consistent in the context.
        # Keeping this and the actions gives the model more information. But it might
        # also confuse it.
        self.turn_actions = set()
        prompt = f"It is your turn to act. The current time is {time_of_day} on day {day} of the adventure."
        if observable_actions:
            prompt += f"\n\n{observable_actions}"

        system_prompt = f"""You have the options to make_note(), speak(), and perform_action(), each usable at most once per turn. You can use recall() at will. You must confirm your turn end by calling end_turn().

Here is the character sheet of the character you're role playing:
{self.cs}"""
        self.context.append_system_message(prompt)
        self.actions.clear()
        await completion.complete(context=self.context,
                                  extra_system_prompt=system_prompt,
                                  gpt_tools=self._describe_methods(),
                                  force_tool=True)

        return self.actions
