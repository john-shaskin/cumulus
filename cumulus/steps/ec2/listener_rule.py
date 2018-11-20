from troposphere import elasticloadbalancingv2 as alb, Ref
from cumulus.chain import step
from cumulus.steps.ec2 import META_TARGET_GROUP_NAME


class ListenerRule(step.Step):

    def __init__(self,
                 base_domain_name,
                 alb_listener_rule,
                 priority,
                 path_pattern=None,
                 host_pattern=None,
                 ):

        step.Step.__init__(self, name='AlbListenerRule')

        self.path_pattern = path_pattern
        self.host_pattern = host_pattern
        self.priority = priority
        self.base_domain_name = base_domain_name
        self.alb_listener_rule = alb_listener_rule

    def handle(self, chain_context):

        template = chain_context.template

        if not (self.path_pattern or self.host_pattern):
            raise RuntimeError("with_listener_rule() requires one of: path_pattern, host_pattern")

        routing_condition = None
        if self.path_pattern:
            routing_condition = alb.Condition(
                Field="path-pattern",
                Values=[self.path_pattern],
            )
        # TODO: support host headers someday
        # elif self.host_pattern:
        #     routing_condition = alb.Condition(
        #         Field="host-header",
        #         Values=[
        #             chain_context.instance_name,
        #             "-",
        #             What do we put here?
        #             ".",
        #             self.base_domain_name
        #         ]
        #     )

        listener_rule = alb.ListenerRule(
            self.name,
            ListenerArn=self.alb_listener_rule,
            Conditions=[routing_condition],
            Actions=[alb.Action(
                Type="forward",
                TargetGroupArn=Ref(chain_context.metadata[META_TARGET_GROUP_NAME])
            )],
            Priority=self.priority,
        )

        template.add_resource(listener_rule)
