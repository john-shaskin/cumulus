import troposphere  # noqa
from termcolor import colored

from cumulus.chain import chaincontext  # noqa
from cumulus.chain.params import TemplateRequirements  # noqa


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
        self._execute_all_steps(chain_context)
        self.validate_template(chain_context)

    def validate_template(self, chain_context):
        """
        :type chain_context: chaincontext.ChainContext

        """

        required_params = chain_context.required_params  # type: TemplateRequirements

        template_params = chain_context.template.parameters

        # Remove all parameters that are already supplied in the template.
        for template_param in template_params:
            if required_params.params.__contains__(template_param):
                required_params.params.remove(template_param)
            print("Required parameter '%s' was satisfied" % template_param)

        unsatisfied_params = ""
        # Build an output string of the remaining params not satisfied
        for param in required_params.params:
            required_line = "Template Requires a parameter named: %s " % param
            unsatisfied_params += required_line + "\n"
            print(colored(required_line, color='red'))

        # If we have params left over, validation failed.
        if len(required_params.params):
            message = ("Template is invalid. Exiting"
                       "all the required params are: ")
            raise AssertionError(message + "\n" + unsatisfied_params)

        if chain_context.instance_name:
            print(colored('chain_context.instance_name is deprecated', color='red'))

    def _execute_all_steps(self, chain_context):
        for step in self._steps:
            print(colored("RUNNING STEP for class %s " % step.__class__, color='yellow'))
            step.handle(chain_context)
