from troposphere import (
    Ref,
    Join,
)


class WindowsUserData:

    def __init__(self,
                 launch_config_name,
                 asg_name,
                 config_sets
                 ):
        self.launch_config_name = launch_config_name
        self.asg_name = asg_name
        self.config_sets = config_sets

    def user_data_for_cfn_init(self):
        """
        :return: A troposphere Join object that contains userdata for use with cfn-init
        :param configsets: The single 'key' value set in the cfn-init Metadata parameter: cloudformation.InitConfigSets
        :type asg_name: String name of the ASG cloudformation resource
        :type launch_config_name: String name of the launch config cloudformation resource
        """
        default_userdata_asg_signal = (
            Join('',
                 [
                     "<powershell>\n",
                     "& ", "$env:ProgramFiles\Amazon\cfn-bootstrap\cfn-init.exe",
                     "         --stack ", Ref("AWS::StackName"),
                     "         --resource ", self.launch_config_name,
                     "         --configsets %s " % self.config_sets,
                     "         --region ", Ref("AWS::Region"), "\n",
                     "# Signal the ASG we are ready\n",
                     "&", "$env:ProgramFiles\Amazon\cfn-signal",
                     " -e ",
                     " $LastExitCode",
                     "    --resource %s" % self.asg_name,
                     "    --stack ", Ref("AWS::StackName"),
                     "    --region ", Ref("AWS::Region"),
                     "\n",
                     "</powershell>"
                 ]))
        return default_userdata_asg_signal
