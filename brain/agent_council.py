
class AgentCouncil:

    def init(self):
        self.agents = []

    def register(self, agent):
        self.agents.append(agent)

    async def deliberate(self, context):

        votes = []

        for agent in self.agents:
            try:
                if hasattr(agent, "act"):
                    votes.append(await agent.act(context))
            except Exception:
                votes.append(None)

        return votes

