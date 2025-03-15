from enum import Enum, auto


class ItemSlot(Enum):
    HEAD = auto()
    NECK = auto()
    CHEST = auto()
    HIPS = auto()
    ARMS = auto()
    LEGS = auto()


class CharacterSheet:
    def __init__(self, full_name: str, location: str, description: str, is_alive: bool = True) -> None:
        self.full_name = full_name
        self.location = location
        self.description = description
        self.is_alive = is_alive

        self.equipment: dict[ItemSlot, list[str]] = {}
        self.inventory: list[str] = []

    async def equip(self, slot: ItemSlot, item: str):
        self.equipment.setdefault(slot, []).append(item.casefold())

    async def unequip(self, slot: ItemSlot, item: str):
        try:
            self.equipment.setdefault(slot, []).remove(item.casefold())
            # Unequipped items go to inventory by default.
            self.pick_up(item)
        except ValueError as e:
            # Eat value error as we attempted to remove non-existing item. That's expected to happen at times.
            pass

    async def pick_up(self, item: str):
        self.inventory.append(item.casefold())

    async def drop(self, item: str):
        try:
            self.inventory.remove(item.casefold())
            # Unequipped items go to inventory by default.
            self.pick_up(item)
        except ValueError as e:
            # Eat value error as we attempted to remove non-existing item. That's expected to happen at times.
            pass

    def render(self):
        return f"""* Full name: {self.full_name}
  - Current location: {self.location}
  - Description: {self.description}
  - Wearing:
{"\n".join(["    - On " + slot + ": " + items for slot,items in self.equipment.items()])}
  - Inventory:
{"\n".join(["    - " + i for i in self.inventory])}"""
