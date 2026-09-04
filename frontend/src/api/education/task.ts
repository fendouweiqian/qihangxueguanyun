import request from '@/utils/request';
import { EaTaskDetailVO, EaTaskForm, EaTaskQuery, EaTaskVO } from './types';
import { AxiosPromise } from 'axios';

export function listTask(query: EaTaskQuery): AxiosPromise<EaTaskVO[]> {
  return request({
    url: '/education/task/list',
    method: 'get',
    params: query
  });
}

export function getTask(taskId: number | string): AxiosPromise<EaTaskVO> {
  return request({
    url: '/education/task/' + taskId,
    method: 'get'
  });
}

export function getTaskDetail(taskId: number | string): AxiosPromise<EaTaskDetailVO> {
  return request({
    url: '/education/task/detail/' + taskId,
    method: 'get'
  });
}

export function addTask(data: EaTaskForm) {
  return request({
    url: '/education/task',
    method: 'post',
    data
  });
}

export function updateTask(data: EaTaskForm) {
  return request({
    url: '/education/task',
    method: 'put',
    data
  });
}

export function delTask(taskId: number | string | Array<number | string>) {
  return request({
    url: '/education/task/' + taskId,
    method: 'delete'
  });
}

export function runTask(taskId: number | string) {
  return request({
    url: '/education/task/run/' + taskId,
    method: 'post'
  });
}

export function runOrderTask(orderId: number | string) {
  return request({
    url: '/education/task/run-order/' + orderId,
    method: 'post'
  });
}

export function runPending(limit = 5) {
  return request({
    url: '/education/task/run-pending',
    method: 'post',
    params: { limit }
  });
}
