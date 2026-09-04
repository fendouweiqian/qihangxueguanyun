import request from '@/utils/request';
import { EaFaceMediaForm, EaFaceMediaQuery, EaFaceMediaVO } from './types';
import { AxiosPromise } from 'axios';

export function listFaceMedia(query: EaFaceMediaQuery): AxiosPromise<EaFaceMediaVO[]> {
  return request({
    url: '/education/face-media/list',
    method: 'get',
    params: query
  });
}

export function getFaceMedia(faceMediaId: number | string): AxiosPromise<EaFaceMediaVO> {
  return request({
    url: '/education/face-media/' + faceMediaId,
    method: 'get'
  });
}

export function addFaceMedia(data: EaFaceMediaForm) {
  return request({
    url: '/education/face-media',
    method: 'post',
    data
  });
}

export function updateFaceMedia(data: EaFaceMediaForm) {
  return request({
    url: '/education/face-media',
    method: 'put',
    data
  });
}

export function delFaceMedia(faceMediaId: number | string | Array<number | string>) {
  return request({
    url: '/education/face-media/' + faceMediaId,
    method: 'delete'
  });
}

export function uploadFaceMedia(file: File, studentId: number | string) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('studentId', String(studentId));
  return request({
    url: '/education/face-media/upload',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
}
