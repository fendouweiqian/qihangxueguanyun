import request from '@/utils/request';
import { EaTenantForm, EaTenantQuery, EaTenantVO } from './types';
import { AxiosPromise } from 'axios';

export function listTenant(query: EaTenantQuery): AxiosPromise<EaTenantVO[]> {
  return request({
    url: '/education/tenant/list',
    method: 'get',
    params: query
  });
}

export function getTenant(tenantId: string): AxiosPromise<EaTenantVO> {
  return request({
    url: '/education/tenant/' + tenantId,
    method: 'get'
  });
}

export function addTenant(data: EaTenantForm) {
  return request({
    url: '/education/tenant',
    method: 'post',
    data
  });
}

export function updateTenant(data: EaTenantForm) {
  return request({
    url: '/education/tenant',
    method: 'put',
    data
  });
}

export function delTenant(tenantId: string | Array<string>) {
  return request({
    url: '/education/tenant/' + tenantId,
    method: 'delete'
  });
}
