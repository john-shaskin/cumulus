import awacs
from awacs import s3
from awacs.aws import Policy, Statement, Allow, Principal
from awacs.sts import AssumeRole
from troposphere import autoscaling, Ref, FindInMap, Base64, ec2, iam
from troposphere.iam import InstanceProfile, Role

from cumulus.chain import step
from cumulus.steps.ec2 import META_SECURITY_GROUP_REF


class LaunchConfig(step.Step):

    def __init__(self,
                 launch_config_name,
                 asg_name,
                 ec2_role_name,
                 meta_data,
                 bucket_name,
                 vpc_id=None,
                 user_data=None):

        step.Step.__init__(self)
        self.launch_config_name = launch_config_name
        self.asg_name = asg_name
        self.ec2_role_name = ec2_role_name
        self.user_data = user_data
        self.meta_data = meta_data
        self.bucket_name = bucket_name
        self.vpc_id = vpc_id

    def handle(self, chain_context):

        template = chain_context.template

        sg_name = "SG%s" % self.asg_name

        launch_config_security_group = ec2.SecurityGroup(
            sg_name,
            GroupDescription=sg_name,
            **self._get_security_group_parameters()
        )

        chain_context.metadata[META_SECURITY_GROUP_REF] = Ref(sg_name)

        user_data = self.user_data

        instance_profile = self._get_instance_profile(chain_context)

        launch_config = autoscaling.LaunchConfiguration(
            self.launch_config_name,
            UserData=Base64(user_data),
            Metadata=self.meta_data,
            IamInstanceProfile=Ref(instance_profile),
            **self._get_launch_configuration_parameters(chain_context)
        )

        template.add_resource(instance_profile)
        template.add_resource(launch_config_security_group)
        template.add_resource(launch_config)

    def _get_security_group_parameters(self):
        config = {}

        if self.vpc_id:
            config['VpcId'] = self.vpc_id

        return config

    def _get_launch_configuration_parameters(self, chain_context):

        asg_sg_list = [chain_context.metadata[META_SECURITY_GROUP_REF]]

        parameters = {
            'ImageId': FindInMap('AmiMap',
                                 Ref("AWS::Region"),
                                 Ref('ImageName')),
            'InstanceType': Ref("InstanceType"),
            'KeyName': Ref("SshKeyName"),
            'SecurityGroups': asg_sg_list,
        }

        return parameters

    def _get_instance_profile(self, chain_context):

        s3readPolicy = iam.Policy(
            PolicyName='S3ReadArtifactBucket',
            PolicyDocument=Policy(
                Statement=[
                    Statement(
                        Effect=Allow,
                        Action=[
                            awacs.s3.GetObject,
                        ],
                        Resource=[s3.ARN(self.bucket_name + "/*")]
                    ),
                    Statement(
                        Effect=Allow,
                        Action=[
                            awacs.s3.ListBucket,
                        ],
                        Resource=[s3.ARN(self.bucket_name)]
                    )
                ]
            )
        )

        cfnrole = chain_context.template.add_resource(Role(
            self.ec2_role_name,
            AssumeRolePolicyDocument=Policy(
                Statement=[
                    Statement(
                        Effect=Allow,
                        Action=[AssumeRole],
                        Principal=Principal("Service", ["ec2.amazonaws.com"])
                    )
                ]
            ),
            Policies=[s3readPolicy]
        ))

        instance_profile = InstanceProfile(
            'InstanceProfile%s' % chain_context.instance_name,
            Roles=[Ref(cfnrole)]
        )
        return instance_profile
