import request from '@/utils/request';
import { EaSchoolCacheForm, EaSchoolCacheQuery, EaSchoolCacheVO } from './types';
import { AxiosPromise } from 'axios';

export function listSchoolCache(query: EaSchoolCacheQuery): AxiosPromise<EaSchoolCacheVO[]> {
  return request({
    url: '/education/school-cache/list',
    method: 'get',
    params: query
  });
}

export function getSchoolCache(cacheId: number | string): AxiosPromise<EaSchoolCacheVO> {
  return request({
    url: '/education/school-cache/' + cacheId,
    method: 'get'
  });
}

export function addSchoolCache(data: EaSchoolCacheForm) {
  return request({
    url: '/education/school-cache',
    method: 'post',
    data
  });
}

export function updateSchoolCache(data: EaSchoolCacheForm) {
  return request({
    url: '/education/school-cache',
    method: 'put',
    data
  });
}

export function delSchoolCache(cacheId: number | string | Array<number | string>) {
  return request({
    url: '/education/school-cache/' + cacheId,
    method: 'delete'
  });
}
