import request from '@/utils/request';
import { EaOrderDetailVO, EaOrderForm, EaOrderQuery, EaOrderVO } from './types';
import { AxiosPromise } from 'axios';

export function listOrder(query: EaOrderQuery): AxiosPromise<EaOrderVO[]> {
  return request({
    url: '/education/order/list',
    method: 'get',
    params: query
  });
}

export function getOrder(orderId: number | string): AxiosPromise<EaOrderVO> {
  return request({
    url: '/education/order/' + orderId,
    method: 'get'
  });
}

export function getOrderDetail(orderId: number | string): AxiosPromise<EaOrderDetailVO> {
  return request({
    url: '/education/order/detail/' + orderId,
    method: 'get'
  });
}

export function addOrder(data: EaOrderForm) {
  return request({
    url: '/education/order',
    method: 'post',
    data
  });
}

export function updateOrder(data: EaOrderForm) {
  return request({
    url: '/education/order',
    method: 'put',
    data
  });
}

export function delOrder(orderId: number | string | Array<number | string>) {
  return request({
    url: '/education/order/' + orderId,
    method: 'delete'
  });
}
