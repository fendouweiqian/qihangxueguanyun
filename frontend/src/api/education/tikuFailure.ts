import request from '@/utils/request';
import { EaTikuFailureQuery, EaTikuFailureVO } from './types';
import { AxiosPromise } from 'axios';

export function listTikuFailure(query: EaTikuFailureQuery): AxiosPromise<EaTikuFailureVO[]> {
  return request({
    url: '/education/tiku-failure/list',
    method: 'get',
    params: query
  });
}
