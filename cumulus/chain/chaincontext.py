from cumulus.chain.params import TemplateRequirements


class ChainContext:

    def __init__(self,
                 template,
                 instance_name=None,
                 auto_param_creation=True
                 ):
        """

        :type template: troposphere.Template
        """
        self._auto_param_creation = auto_param_creation
        self._instance_name = instance_name
        self._template = template
        self._metadata = {}
        self._required_params = TemplateRequirements()

    @property
    def template(self):
        return self._template

    @property
    def metadata(self):
        """
        Steps can write data here to be used later in the chain.
        Example: Code dev_tools initial step might create an s3 bucket
                 Subsequent steps might want to reference this.
                 It could be a string, or even a troposphere Ref object.
        :return:
        """
        return self._metadata

    @property
    def instance_name(self):
        # TODO: validate instance name for s3 compatibility (cuz it could be used there)
        return self._instance_name

    @property
    def required_params(self):
        return self._required_params

    @property
    def auto_param_creation(self):
        return self._auto_param_creation
