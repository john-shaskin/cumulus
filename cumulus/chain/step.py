from cumulus.chain import chaincontext # noqa


class Step:
    """
    Define an interface for handling requests.
    """

    def __init__(self, name='UnNamed'):
        """

        :type name: basestring Friendly name of the step to be used in logical naming
        """
        self.name = name

    def handle(self, chain_context):
        # type: (chaincontext.ChainContext) -> None
        raise NotImplementedError("handle must be implemented")
