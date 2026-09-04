import request from '@/utils/request';
import { EaSchoolForm, EaSchoolQuery, EaSchoolVO } from './types';
import { AxiosPromise } from 'axios';

export function listSchool(query: EaSchoolQuery): AxiosPromise<EaSchoolVO[]> {
  return request({
    url: '/education/school/list',
    method: 'get',
    params: query
  });
}

export function getSchool(schoolId: number | string): AxiosPromise<EaSchoolVO> {
  return request({
    url: '/education/school/' + schoolId,
    method: 'get'
  });
}

export function addSchool(data: EaSchoolForm) {
  return request({
    url: '/education/school',
    method: 'post',
    data
  });
}

export function updateSchool(data: EaSchoolForm) {
  return request({
    url: '/education/school',
    method: 'put',
    data
  });
}

export function delSchool(schoolId: number | string | Array<number | string>) {
  return request({
    url: '/education/school/' + schoolId,
    method: 'delete'
  });
}
