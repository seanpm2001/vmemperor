/**
 *
 * VmsettingsForm
 *
 */

import React, {useCallback, useState} from 'react';
import {PowerState, VmAccessSetMutation, VmActions, VmEditOptions, VmInfo} from "../../generated-models";
import Overview from './subforms/overview';
import {Badge, Col, Nav, NavItem, NavLink, Row, TabContent, TabPane} from 'reactstrap';
import classnames from 'classnames';
import Vncview from '../../containers/Vncview';
import Network from "./subforms/network";
import Storage from "./subforms/storage";
import AccessView from '../../components/AccessView';
import Vm = VmInfo.Vm;
import VmAccessSet = VmAccessSetMutation.VmAccessSet;
import XenObjectHeader from "../XenObjectHeader";


interface Props {
  vm: Vm;
}

enum Tab {
  Overview = 'overview',
  CPU = 'cpu',
  VNC = 'vnc',
  Access = 'access',
  Storage = 'storage',
  Network = 'network',
}


const VmsettingsForm = ({vm}: Props) => {
  const [activeTab, setActiveTab] = useState(Tab.Overview);
  const [vncActivated, setVncActivated] = useState(false);

  const toggleTab = useCallback((tab: Tab) => {
    if (activeTab !== tab) {
      setActiveTab(tab);
    }
    if (tab === Tab.VNC && !vncActivated) {
      setVncActivated(true);
    }
  }, [activeTab, vncActivated]);

  if (activeTab === Tab.VNC && vm.powerState !== PowerState.Running) {
    setVncActivated(false);
    setActiveTab(Tab.Overview);
  }
  return (
    <div>
      <XenObjectHeader
        xenObject={vm}
        editMutationName={"vm"}
        editMutation={VmEditOptions.Document}
      >
        <Badge color="primary">{vm.powerState}</Badge>
        {vm.osVersion &&
        (<Badge color="success">{vm.osVersion.name}</Badge>)}
      </XenObjectHeader>

      <Nav tabs={true}>
        <NavItem>
          <NavLink
            className={classnames({active: activeTab === Tab.Overview})}
            onClick={() => {
              toggleTab(Tab.Overview);
            }}
          >
            Overview
          </NavLink>
        </NavItem>
        <NavItem>
          <NavLink
            className={classnames({active: activeTab === Tab.CPU})}
            onClick={() => {
              toggleTab(Tab.CPU);
            }}
          >
            CPU & Memory
          </NavLink>
        </NavItem>
        <NavItem>
          <NavLink
            className={classnames({active: activeTab === Tab.VNC})}
            onClick={() => {
              toggleTab(Tab.VNC);
            }}
            disabled={vm.powerState !== PowerState.Running || !vm.myActions.includes(VmActions.Vnc)}
          >
            VNC
          </NavLink>
        </NavItem>
        <NavItem>
          <NavLink
            className={classnames({active: activeTab === Tab.Access})}
            onClick={() => {
              toggleTab(Tab.Access);
            }}
          >
            Access
          </NavLink>
        </NavItem>
        <NavItem>
          <NavLink
            className={classnames({active: activeTab === Tab.Storage})}
            onClick={() => {
              toggleTab(Tab.Storage);
            }}
          >
            Storage
          </NavLink>
        </NavItem>
        <NavItem>
          <NavLink
            className={classnames({active: activeTab === Tab.Network})}
            onClick={() => {
              toggleTab(Tab.Network);
            }}
          >
            Network
          </NavLink>
        </NavItem>
      </Nav>
      <TabContent activeTab={activeTab}>
        <TabPane tabId={Tab.Overview}>
          <Row>
            <Col sm="12">
              <Overview vm={vm}/>
            </Col>
          </Row>
        </TabPane>
        <TabPane tabId={Tab.CPU}>
          <Row>
            <Col sm="12">
              
            </Col>
          </Row>
        </TabPane>
        <TabPane tabId={Tab.Access}>
          <Row>
            <Col sm="12">
              {<AccessView
                data={vm}
                ALL={VmActions.All}
                mutationName="vmAccessSet"
                mutationNode={VmAccessSetMutation.Document}
              />}
            </Col>
          </Row>
        </TabPane>
        <TabPane tabId={Tab.Storage}>
          <Row>
            <Col sm="12">
              {<Storage
                vm={vm}/>}
            </Col>
          </Row>
        </TabPane>
        <TabPane tabId={Tab.VNC}>
          {
            vncActivated && (
              <Vncview vm={vm}/>
            ) || (<h1>NO VNC HERE</h1>)
          }
        </TabPane>
        <TabPane tabId={Tab.Network}>
          <Row>
            <Col sm="12">
              {<Network
                vm={vm}
              />}
            </Col>
          </Row>
        </TabPane>
      </TabContent>
    </div>
  )
};

export default VmsettingsForm;
