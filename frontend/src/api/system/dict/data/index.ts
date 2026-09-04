import request from '@/utils/request';
import { AxiosPromise } from 'axios';
import { DictDataForm, DictDataQuery, DictDataVO } from './types';

export function getDicts(dictType: string): AxiosPromise<DictDataVO[]> {
  return request({
    url: '/system/dict/data/type/' + dictType,
    method: 'get'
  });
}

export function listData(query: DictDataQuery): AxiosPromise<DictDataVO[]> {
  return request({
    url: '/system/dict/data/list',
    method: 'get',
    params: query
  });
}

export function getData(dictCode: string | number): AxiosPromise<DictDataVO> {
  return request({
    url: '/system/dict/data/' + dictCode,
    method: 'get'
  });
}

export function addData(data: DictDataForm) {
  return request({
    url: '/system/dict/data',
    method: 'post',
    data
  });
}

export function updateData(data: DictDataForm) {
  return request({
    url: '/system/dict/data',
    method: 'put',
    data
  });
}

export function delData(dictCode: string | number | Array<string | number>) {
  return request({
    url: '/system/dict/data/' + dictCode,
    method: 'delete'
  });
}
