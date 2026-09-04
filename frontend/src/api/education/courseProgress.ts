import request from '@/utils/request';
import { EaCourseProgressForm, EaCourseProgressQuery, EaCourseProgressVO } from './types';
import { AxiosPromise } from 'axios';

export function listCourseProgress(query: EaCourseProgressQuery): AxiosPromise<EaCourseProgressVO[]> {
  return request({
    url: '/education/course-progress/list',
    method: 'get',
    params: query
  });
}

export function getCourseProgress(progressId: number | string): AxiosPromise<EaCourseProgressVO> {
  return request({
    url: '/education/course-progress/' + progressId,
    method: 'get'
  });
}

export function addCourseProgress(data: EaCourseProgressForm) {
  return request({
    url: '/education/course-progress',
    method: 'post',
    data
  });
}

export function updateCourseProgress(data: EaCourseProgressForm) {
  return request({
    url: '/education/course-progress',
    method: 'put',
    data
  });
}

export function delCourseProgress(progressId: number | string | Array<number | string>) {
  return request({
    url: '/education/course-progress/' + progressId,
    method: 'delete'
  });
}
