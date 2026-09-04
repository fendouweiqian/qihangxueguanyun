import request from '@/utils/request';
import { EaRechargeForm, EaRechargeQuery, EaRechargeVO } from './types';
import { AxiosPromise } from 'axios';

export function listRecharge(query: EaRechargeQuery): AxiosPromise<EaRechargeVO[]> {
  return request({
    url: '/education/recharge/list',
    method: 'get',
    params: query
  });
}

export function getRecharge(rechargeId: number | string): AxiosPromise<EaRechargeVO> {
  return request({
    url: '/education/recharge/' + rechargeId,
    method: 'get'
  });
}

export function addRecharge(data: EaRechargeForm) {
  return request({
    url: '/education/recharge',
    method: 'post',
    data
  });
}
