from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import EC2SubnetIdList, CFNCommaDelimitedList, CFNString, CFNNumber, \
    EC2KeyPairKeyName
from troposphere import cloudformation, ec2, Ref

from cumulus.chain import chain, chaincontext
from cumulus.components.userdata.linux import LinuxUserData
from cumulus.steps.ec2 import scaling_group, launch_config, block_device_data, ingress_rule, target_group, dns, \
    alb_port, listener_rule


class WebsiteSimple(Blueprint):
    VARIABLES = {
        'env': {
            'type': CFNString
        },
        'IAlbListener': {
            'type': CFNString,
            'description': 'From the ALB',
        },
        'AlbCanonicalHostedZoneID': {
            'type': CFNString,
            'description': 'From the ALB',
            'default': 'acm',
        },
        'AlbDNSName': {
            'type': CFNString,
            'description': 'From the ALB',
            'default': 'acm',
        },
        'AlbSg': {
            'type': CFNString,
            'description': 'From the ALB',
        },
        'InstanceType': {'type': CFNString,
                         'description': 'EC2 Instance Type',
                         'default': 't2.micro'},
        'SshKeyName': {'type': EC2KeyPairKeyName},
        'ImageName': {
            'type': CFNString,
            'description': 'The image name to use from the AMIMap (usually '
                           'found in the config file.)'},
        'BaseDomain': {
            'type': CFNString},
        'MinSize': {'type': CFNNumber,
                    'description': 'Minimum # of instances.',
                    'default': '1'},
        'MaxSize': {'type': CFNNumber,
                    'description': 'Maximum # of instances.',
                    'default': '5'},
        'PrivateSubnets': {'type': EC2SubnetIdList,
                           'description': 'Subnets to deploy private '
                                          'instances in.'},
        'AvailabilityZones': {'type': CFNCommaDelimitedList,
                              'description': 'Availability Zones to deploy '
                                             'instances in.'},
        'VpcId': {'type': CFNString,
                  'description': 'Vpc Id'},
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
                            'command': 'nohup python -m SimpleHTTPServer 8000 &'
                        },
                    }
                )
            )
        )
        return metadata

    def create_template(self):
        t = self.template
        t.add_description("Acceptance Tests for cumulus scaling groups")

        the_chain = chain.Chain()

        application_port = "8000"

        instance_name = self.context.namespace + "testAlb"

        launch_config_name = 'Lc%s' % instance_name
        asg_name = 'Asg%s' % instance_name
        ec2_role_name = 'Ec2RoleName%s' % instance_name

        the_chain.add(launch_config.LaunchConfig(launch_config_name=launch_config_name,
                                                 asg_name=asg_name,
                                                 ec2_role_name=ec2_role_name,
                                                 vpc_id=Ref('VpcId'),
                                                 meta_data=self.get_metadata(),
                                                 bucket_name=self.context.bucket_name,
                                                 user_data=LinuxUserData.user_data_for_cfn_init(
                                                     launch_config_name=launch_config_name,
                                                     asg_name=asg_name,
                                                     configsets='default'
                                                 )))

        the_chain.add(ingress_rule.IngressRule(
            port_to_open="22",
            name="TestAlbPort22",
            cidr="10.0.0.0/8"
        ))

        the_chain.add(ingress_rule.IngressRule(
            port_to_open=application_port,
            name="TestAlbPort8000",
            cidr="10.0.0.0/8"
        ))

        the_chain.add(block_device_data.BlockDeviceData(ec2.BlockDeviceMapping(
            DeviceName="/dev/xvda",
            Ebs=ec2.EBSBlockDevice(
                VolumeSize="40"
            ))))

        the_chain.add(target_group.TargetGroup(
            port=application_port,
            name='%sTargetGroup' % instance_name,
            vpc_id=Ref("VpcId")
        ))

        the_chain.add(scaling_group.ScalingGroup(name=asg_name,
                                                 launch_config_name=launch_config_name))

        the_chain.add(dns.Dns(
            namespace=self.context.namespace,
            base_domain=Ref("BaseDomain"),
            hosted_zone_id=Ref("AlbCanonicalHostedZoneID"),
            dns_name=Ref("AlbDNSName"),
        ))

        the_chain.add(alb_port.AlbPort(
            name="AlbPortToOpen8000",
            port_to_open=application_port,
            alb_sg_name="AlbSg",
        ))

        the_chain.add(listener_rule.ListenerRule(
            base_domain_name=Ref("BaseDomain"),
            alb_listener_rule=Ref("IAlbListener"),
            path_pattern="/*",
            priority="2"
        ))

        chain_context = chaincontext.ChainContext(
            template=t,
            instance_name=instance_name
        )

        the_chain.run(chain_context)
