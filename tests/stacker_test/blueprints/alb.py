from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import EC2VPCId, EC2SubnetIdList, CFNCommaDelimitedList, CFNString, CFNNumber

from cumulus.chain import chain, chaincontext
from cumulus.steps.ec2 import alb


class Alb(Blueprint):
    VARIABLES = {
        'VpcId': {'type': EC2VPCId, 'description': 'Vpc Id'},
        'PrivateSubnets': {
            'type': EC2SubnetIdList,
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
        'ALBHostName': {
            'type': CFNString,
            'description': 'A hostname to give to the ALB. If not given '
                           'no ALB will be created.',
            'default': ''},
        'ALBCertName': {
            'type': CFNString,
            'description': 'The SSL certificate name to use on the ALB.',
            'default': ''},
        'ALBCertType': {
            'type': CFNString,
            'description': 'The SSL certificate type to use on the ALB.',
            'default': 'acm'},
    }

    def create_template(self):

        t = self.template
        t.add_description("Acceptance Tests for cumulus scaling groups")

        the_chain = chain.Chain()

        the_chain.add(alb.Alb(prefix="websitesimple"))

        chain_context = chaincontext.ChainContext(
            template=t,
        )

        the_chain.run(chain_context)
