from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import EC2VPCId, EC2SubnetIdList, CFNCommaDelimitedList, CFNString, CFNNumber, \
    EC2KeyPairKeyName
from troposphere import cloudformation, ec2, Ref

from cumulus.chain import chain, chaincontext
from cumulus.steps.ec2 import scaling_group, launch_config, block_device_data, ingress_rule

NAME_SUFFIX = "scalinggroupsimple"


class ScalingGroupSimple(Blueprint):
    VARIABLES = {
        'VpcId': {'type': EC2VPCId,
                  'description': 'Vpc Id'},
        'PrivateSubnets': {'type': EC2SubnetIdList,
                           'description': 'Subnets to deploy private '
                                          'instances in.'},
        'AvailabilityZones': {'type': CFNCommaDelimitedList,
                              'description': 'Availability Zones to deploy '
                                             'instances in.'},
        'InstanceType': {'type': CFNString,
                         'description': 'EC2 Instance Type',
                         'default': 't2.micro'},
        'MinSize': {'type': CFNNumber,
                    'description': 'Minimum # of instances.',
                    'default': '1'},
        'MaxSize': {'type': CFNNumber,
                    'description': 'Maximum # of instances.',
                    'default': '5'},
        'SshKeyName': {'type': EC2KeyPairKeyName},
        'ImageName': {
            'type': CFNString,
            'description': 'The image name to use from the AMIMap (usually '
                           'found in the config file.)'},
    }

    def get_metadata(self):
        metadata = cloudformation.Metadata(
            cloudformation.Init(
                cloudformation.InitConfigSets(
                    default=['install_and_run']
                ),
                install_and_run=cloudformation.InitConfig(
                    commands={
                        '01-startup': {
                            'command': 'touch thisfilemeansiworked'
                        },
                    }
                )
            )
        )
        return metadata

    def create_template(self):
        t = self.template
        t.add_description("Acceptance Tests for cumulus scaling groups")

        # TODO: give to builder
        the_chain = chain.Chain()

        the_chain.add(launch_config.LaunchConfig(prefix=NAME_SUFFIX,
                                                 vpc_id=Ref('VpcId'),
                                                 bucket_name=self.context.bucket_name,
                                                 meta_data=self.get_metadata()))

        the_chain.add(ingress_rule.IngressRule(
            port_to_open="22",
            cidr='10.0.0.0/8'
        ))

        the_chain.add(block_device_data.BlockDeviceData(ec2.BlockDeviceMapping(
            DeviceName="/dev/xvda",
            Ebs=ec2.EBSBlockDevice(
                VolumeSize="40"
            ))))

        the_chain.add(scaling_group.ScalingGroup())

        chain_context = chaincontext.ChainContext(
            template=t,
        )

        the_chain.run(chain_context)
