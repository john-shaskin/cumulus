from troposphere import Ref, iam

from cumulus.chain import step

EC2_ROLE_NAME = "Ec2RoleName"


class InstanceProfilePolicy(step.Step):

    def __init__(self,
                 policy):
        step.Step.__init__(self, name='InstanceProfilePolicy')
        self.policy = policy

    def handle(self, chain_context):
        template = chain_context.template

        template.add_resource(iam.PolicyType(
            self.name,
            PolicyName=self.name,
            PolicyDocument=self.policy,
            Roles=[Ref(EC2_ROLE_NAME)],
        ))
