import request from '@/utils/request';
import { EaRunnerNodeForm, EaRunnerNodeQuery, EaRunnerNodeVO } from './types';
import { AxiosPromise } from 'axios';

export function listRunnerNode(query: EaRunnerNodeQuery): AxiosPromise<EaRunnerNodeVO[]> {
  return request({
    url: '/education/runner-node/list',
    method: 'get',
    params: query
  });
}

export function getRunnerNode(nodeId: number | string): AxiosPromise<EaRunnerNodeVO> {
  return request({
    url: '/education/runner-node/' + nodeId,
    method: 'get'
  });
}

export function addRunnerNode(data: EaRunnerNodeForm) {
  return request({
    url: '/education/runner-node',
    method: 'post',
    data
  });
}

export function updateRunnerNode(data: EaRunnerNodeForm) {
  return request({
    url: '/education/runner-node',
    method: 'put',
    data
  });
}

export function delRunnerNode(nodeId: number | string | Array<number | string>) {
  return request({
    url: '/education/runner-node/' + nodeId,
    method: 'delete'
  });
}
