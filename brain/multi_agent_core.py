class MultiAgentCore:

    def __init__(self):
        self.agents = {}

    def register_agent(self, name, agent):
        self.agents[name] = agent

    async def run(self, context):

        results = {}

        for name, agent in self.agents.items():
            try:
                results[name] = await agent.act(context)
            except:
                results[name] = None

        return results
