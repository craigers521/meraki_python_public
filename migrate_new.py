#!/usr/bin/python3

"""
using new meraki python module
"""

import sys
import meraki
import getopt
import json
from datetime import datetime

# Prints a line of text that is meant for the user to read
def printusertext(p_message):
    print('# %s' % p_message)


# Prints help text
def printhelp():
    printusertext('This script finds all networks matching a network tag (configured on the')
    printusertext('Organization > Overview page\'s table), and binds those networks to the')
    printusertext('target template (by name). The network\'s current VLANs for unique subnets')
    printusertext('will be reconfigured after binding to the target template, since binding to')
    printusertext('a template regenerates these unique subnets. Also, if the network is')
    printusertext('currently bound to a different template, it will be unbound from that')
    printusertext('current template first.')
    printusertext('Optionally, auto-bind the network\'s switches to profiles, as specified in the')
    printusertext('API call: https://dashboard.meraki.com/api_docs#bind-a-network-to-a-template')
    printusertext('')
    printusertext('Usage:')
    printusertext('python migrate.py -k <api_key> -o <org_id> -t <target_template_name>')
    printusertext('\t-n <network_tag> [-s <auto_bind>]')
    printusertext('If the target template\'s name has spaces, include quotes around it.')


def main(argv):
    # Set default values for command line arguments
    api_key = org_id = arg_template = arg_tag = arg_switch = 'null'

    # Get command line arguments
    try:
        opts, args = getopt.getopt(argv, 'hk:o:t:n:s:')
    except getopt.GetoptError:
        # printhelp()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            printhelp()
            sys.exit()
        elif opt == '-k':
            api_key = arg
        elif opt == '-o':
            org_id = arg
        elif opt == '-t':
            arg_template = arg
        elif opt == '-n':
            arg_tag = arg
        elif opt == '-s':
            arg_switch = arg

    # Check if all parameters are required parameters have been given
    if api_key == 'null' or org_id == 'null' or arg_template == 'null' or arg_tag == 'null':
        printhelp()
        sys.exit(2)
    '''if arg_switch not in ('null', 'True', 'true', 'False', 'false'):
        printhelp()
        sys.exit(2)'''
    # start API session
    m = meraki.DashboardAPI(api_key)

    # Find all networks matching input tag
    networks = m.networks.getOrganizationNetworks(org_id)
    tagged_networks = [network for network in networks if network['tags'] and arg_tag in network['tags']]

    # find templates
    templates = m.config_templates.getOrganizationConfigTemplates(org_id)
    template_ids = [template['id'] for template in templates]
    template_names = [template['name'] for template in templates]
    target_template_id = template_ids[template_names.index(arg_template)]

    # Tally up number of networks that are either unbound or currently bound to other templates
    unbound_count = 0
    for network in tagged_networks:
        if 'configTemplateId' in network:
            index = template_ids.index(network['configTemplateId'])
            if 'count' in templates[index]:
                templates[index]['count'] += 1
            else:
                templates[index]['count'] = 1
        else:
            unbound_count += 1

    # Confirm with user number of networks to be updated
    print('Found a grand total of {0} networks with the tag {1}:'.format(len(tagged_networks), arg_tag))
    if unbound_count > 0:
        print('{0} networks are currently unbound, not bound to any template'.format(unbound_count))
    for template in templates:
        if 'count' in template and template['count'] > 0:
            print('{0} networks are currently bound to template {1}'.format(template['count'], template['name']))
    continue_run = input('Continue to update by binding all {0} networks to the {1} template? (Y/N) '.format(len(tagged_networks), arg_template))
    if continue_run == "N":
        exit()

    # Update and bind networks to template
    for network in tagged_networks:
        # gather current data
        net_id = network['id']
        net_name = network['name']
        old_vlans = m.vlans.getNetworkVlans(net_id)
        old_vlan_ids = [vlan['id'] for vlan in old_vlans]
        old_uplink = m.uplink_settings.getNetworkUplinkSettings(net_id)

        # unbind/rebind
        if 'configTemplateId' in network:
            template_name = template_names[template_ids.index(network['configTemplateId'])]
            print('Unbinding network {0} from current template {1}'.format(net_name, template_name))
            m.networks.unbindNetwork(net_id)
        print('Binding network {0} to target template {1}'.format(net_name, arg_template))
        if arg_switch in ('True', 'true'):
            m.networks.bindNetwork(net_id, target_template_id, autoBind=True)
        else:
            m.networks.bindNetwork(net_id, target_template_id)

        # update uplink
        m.uplink_settings.updateNetworkUplinkSettings(net_id, **old_uplink)

        # update vlans
        new_vlans = m.vlans.getNetworkVlans(net_id)
        for new_vlan in new_vlans:
            vlan_id = new_vlan['id']
            old_vlan = old_vlans[old_vlan_ids.index(vlan_id)]
            if new_vlan['subnet'] != old_vlan['subnet'] or new_vlan['applianceIp'] != old_vlan['applianceIp']:
                m.vlans.updateNetworkVlan(net_id, vlan_id, subnet=old_vlan['subnet'], applianceIp=old_vlan['applianceIp'])


if __name__ == '__main__':
    startTime = datetime.now()
    print('Starting script at: %s' % startTime)
    print('Arguments entered: %s' % sys.argv[1:])
    main(sys.argv[1:])
    print('Ending script at: %s' % datetime.now())
    print('Total run time: %s' % (datetime.now() - startTime))

