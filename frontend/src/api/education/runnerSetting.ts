import request from '@/utils/request';
import { EaRunnerSettingForm, EaRunnerSettingQuery, EaRunnerSettingVO } from './types';
import { AxiosPromise } from 'axios';

export function listRunnerSetting(query: EaRunnerSettingQuery): AxiosPromise<EaRunnerSettingVO[]> {
  return request({
    url: '/education/runner-setting/list',
    method: 'get',
    params: query
  });
}

export function getRunnerSetting(settingId: number | string): AxiosPromise<EaRunnerSettingVO> {
  return request({
    url: '/education/runner-setting/' + settingId,
    method: 'get'
  });
}

export function addRunnerSetting(data: EaRunnerSettingForm) {
  return request({
    url: '/education/runner-setting',
    method: 'post',
    data
  });
}

export function updateRunnerSetting(data: EaRunnerSettingForm) {
  return request({
    url: '/education/runner-setting',
    method: 'put',
    data
  });
}

export function delRunnerSetting(settingId: number | string | Array<number | string>) {
  return request({
    url: '/education/runner-setting/' + settingId,
    method: 'delete'
  });
}
