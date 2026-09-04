import request from '@/utils/request';
import { EaPlatformForm, EaPlatformQuery, EaPlatformVO } from './types';
import { AxiosPromise } from 'axios';

export function listPlatform(query: EaPlatformQuery): AxiosPromise<EaPlatformVO[]> {
  return request({
    url: '/education/platform/list',
    method: 'get',
    params: query
  });
}

export function getPlatform(platformId: number | string): AxiosPromise<EaPlatformVO> {
  return request({
    url: '/education/platform/' + platformId,
    method: 'get'
  });
}

export function addPlatform(data: EaPlatformForm) {
  return request({
    url: '/education/platform',
    method: 'post',
    data
  });
}

export function updatePlatform(data: EaPlatformForm) {
  return request({
    url: '/education/platform',
    method: 'put',
    data
  });
}

export function delPlatform(platformId: number | string | Array<number | string>) {
  return request({
    url: '/education/platform/' + platformId,
    method: 'delete'
  });
}
