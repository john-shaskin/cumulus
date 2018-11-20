from troposphere import Ref, autoscaling
from troposphere.autoscaling import Tag as ASTag
from troposphere.policies import UpdatePolicy, AutoScalingReplacingUpdate, AutoScalingRollingUpdate

from cumulus.chain import step
from cumulus.steps.ec2 import META_TARGET_GROUP_NAME

LAUNCH_CONFIG_NAME = "LaunchConfig"


class ScalingGroup(step.Step):

    def __init__(self,
                 use_update_policy=True,
                 ):
        """
        :type launch_type: LaunchType: the type of the ec2 that will be created
        """
        step.Step.__init__(self,
                           name='ScalingGroup')

        # Set default resource names for those not injected
        self.use_update_policy = use_update_policy

    def handle(self, chain_context):

        template = chain_context.template

        template.add_resource(autoscaling.AutoScalingGroup(
            self.name,
            **self._get_autoscaling_group_parameters(chain_context=chain_context,
                                                     launch_config_name=LAUNCH_CONFIG_NAME)))

    def _get_autoscaling_group_parameters(self, chain_context, launch_config_name):

        config = {
            'AvailabilityZones': Ref("AvailabilityZones"),  # Not really required in this case (yet)
            'LaunchConfigurationName': Ref(launch_config_name),
            'MinSize': Ref("MinSize"),
            'MaxSize': Ref("MaxSize"),
            'VPCZoneIdentifier': Ref("PrivateSubnets"),
            'Tags': [ASTag('Name', self.name, True)],
        }

        if META_TARGET_GROUP_NAME in chain_context.metadata:
            config['TargetGroupARNs'] = [Ref(chain_context.metadata[META_TARGET_GROUP_NAME])]

        if self.use_update_policy:
            update_policy = UpdatePolicy(
                AutoScalingReplacingUpdate=AutoScalingReplacingUpdate(
                    WillReplace=True,
                ),
                AutoScalingRollingUpdate=AutoScalingRollingUpdate(
                    PauseTime='PT5M',
                    MinInstancesInService="1",
                    MaxBatchSize='1',
                    WaitOnResourceSignals=True
                )
            )
            config['UpdatePolicy'] = update_policy

        return config
