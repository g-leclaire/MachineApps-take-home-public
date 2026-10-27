import asyncio

from robot_control import GantryMachine, Triggers

async def main() -> None:
    machine = GantryMachine()
    await machine.start()
    machine.trigger(Triggers.begin_sequence.name)
    
    while machine.state not in {"ready", "fault"}:
        await asyncio.sleep(0.05)

    await machine.stop_background_tasks()


asyncio.run(main())