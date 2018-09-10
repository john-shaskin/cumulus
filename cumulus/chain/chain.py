from termcolor import colored


class Chain:

    def __init__(self):
        self._steps = []

    @property
    def steps(self):
        return self._steps

    def add(self, step):
        self._steps.append(step)

    def run(self, chain_context):
        """

        :type chain_context: chaincontext.ChainContext
        """
        for step in self._steps:
            print(colored("RUNNING STEP for class %s " % step.__class__, color='yellow'))
            step.handle(chain_context)
