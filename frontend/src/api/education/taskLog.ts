import request from '@/utils/request';
import { EaTaskLogQuery, EaTaskLogVO } from './types';
import { AxiosPromise } from 'axios';

export function listTaskLog(query: EaTaskLogQuery): AxiosPromise<EaTaskLogVO[]> {
  return request({
    url: '/education/task-log/list',
    method: 'get',
    params: query
  });
}
