# Copyright 2012 Knowledge Economy Developments Ltd
# 
# Henry Gomersall
# heng@kedevelopments.co.uk
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pyfftw import FFTW, n_byte_align, n_byte_align_empty, forget_wisdom
import pyfftw
import numpy
from timeit import Timer
import time

import unittest

from test_pyfftw_base import FFTWBaseTest, run_test_suites

# We make this 1D case not inherit from FFTWBaseTest.
# It needs to be combined with FFTWBaseTest to work.
# This allows us to separate out tests that are use
# in multiple locations.
class Complex64FFTW1DTest(object):
            
    def test_time(self):
        
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']
        
        axes=(-1,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        fft, ifft = self.run_validate_fft(a, b, axes)

        self.timer_routine(fft.execute, 
                lambda: self.np_fft_comparison(a))
        self.assertTrue(True)

    def test_1d(self):
        in_shape = self.input_shapes['1d']
        out_shape = self.output_shapes['1d']

        axes=(0,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        self.run_validate_fft(a, b, axes)

    def test_multiple_1d(self):
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']
        
        axes=(-1,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        self.run_validate_fft(a, b, axes)

    def test_default_args(self):
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']
        
        a, b = self.create_test_arrays(in_shape, out_shape)
        
        fft = FFTW(a,b)
        fft.execute()
        ref_b = self.reference_fftn(a, axes=(-1,))
        self.assertTrue(numpy.allclose(b, ref_b, rtol=1e-2, atol=1e-3))

    def test_time_with_array_update(self):
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']
        
        axes=(-1,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        fft, ifft = self.run_validate_fft(a, b, axes)
        
        def fftw_callable():
            fft.update_arrays(a,b)
            fft.execute()

        self.timer_routine(fftw_callable, 
                lambda: self.np_fft_comparison(a))

        self.assertTrue(True)
        
    def test_planning_time_limit(self):
        in_shape = self.input_shapes['1d']
        out_shape = self.output_shapes['1d']

        axes=(0,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        # run this a few times
        runs = 10
        t1 = time.time()
        for n in xrange(runs):
            forget_wisdom()
            fft = FFTW(a, b, axes=axes)

        unlimited_time = (time.time() - t1)/runs

        time_limit = (unlimited_time)/8

        # Now do it again but with an upper limit on the time
        t1 = time.time()
        for n in xrange(runs):
            forget_wisdom()
            fft = FFTW(a, b, axes=axes, planning_timelimit=time_limit)

        limited_time = (time.time() - t1)/runs

        # Give a 2x margin 
        self.assertTrue(limited_time < time_limit*2)

    def test_invalid_planning_time_limit(self):
        in_shape = self.input_shapes['1d']
        out_shape = self.output_shapes['1d']

        axes=(0,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        self.assertRaisesRegexp(TypeError, 'Invalid planning timelimit',
                FFTW, *(a,b, axes), **{'planning_timelimit': 'foo'})
    
    def test_planner_flags(self):
        '''Test all the planner flags on a small array
        '''
        in_shape = self.input_shapes['small_1d']
        out_shape = self.output_shapes['small_1d']
        
        axes=(0,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        for each_flag in pyfftw.pyfftw._flag_dict:
            fft, ifft = self.run_validate_fft(a, b, axes, 
                    flags=(each_flag,))

            self.assertTrue(each_flag in fft.flags)
            self.assertTrue(each_flag in ifft.flags)

        # also, test no flags (which should still work)
        fft, ifft = self.run_validate_fft(a, b, axes, 
                    flags=())

    def test_destroy_input(self):
        '''Test the destroy input flag
        '''
        # We can't really test it actually destroys the input, as it might
        # not (plus it's not exactly something we want).
        # It's enough just to check it runs ok with that flag.
        in_shape = self.input_shapes['1d']
        out_shape = self.output_shapes['1d']

        axes=(0,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        self.run_validate_fft(a, b, axes, 
                flags=('FFTW_ESTIMATE','FFTW_DESTROY_INPUT'))

    def test_invalid_flag_fail(self):
        '''Test passing a garbage flag fails
        '''
        in_shape = self.input_shapes['1d']
        out_shape = self.output_shapes['1d']

        axes=(0,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        self.assertRaisesRegexp(ValueError, 'Invalid flag', 
                self.run_validate_fft, *(a, b, axes), 
                **{'flags':('garbage',)})

    def test_alignment(self):
        '''Test to see if the alignment is returned correctly
        '''
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']

        input_dtype_alignment = self.get_input_dtype_alignment()
        output_dtype_alignment = self.get_output_dtype_alignment()
        
        axes=(-1,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        a = n_byte_align(a, 16)
        b = n_byte_align(b, 16)

        fft, ifft = self.run_validate_fft(a, b, axes, 
                force_unaligned_data=True)

        a, b = self.create_test_arrays(in_shape, out_shape)

        a = n_byte_align(a, 16)
        b = n_byte_align(b, 16)

        a_orig = a.copy()
        b_orig = b.copy()

        # Offset from 16 byte aligned to guarantee it's not
        # 16 byte aligned
        a__ = n_byte_align_empty(
                numpy.prod(in_shape)*a.itemsize + input_dtype_alignment, 
                16, dtype='int8')
        
        a_ = (a__[input_dtype_alignment:]
                .view(dtype=self.input_dtype).reshape(*in_shape))
        a_[:] = a 
        
        b__ = n_byte_align_empty(
                numpy.prod(out_shape)*b.itemsize + input_dtype_alignment, 
                16, dtype='int8')
        
        b_ = (b__[input_dtype_alignment:]
                .view(dtype=self.output_dtype).reshape(*out_shape))
        b_[:] = b

        a[:] = a_orig        
        fft, ifft = self.run_validate_fft(a, b, axes, 
                create_array_copies=False)

        self.assertTrue(fft.input_alignment == 16)
        self.assertTrue(fft.output_alignment == 16)

        a[:] = a_orig
        fft, ifft = self.run_validate_fft(a, b_, axes, 
                create_array_copies=False)

        self.assertTrue(fft.input_alignment == input_dtype_alignment)
        self.assertTrue(fft.output_alignment == output_dtype_alignment)

        a_[:] = a_orig        
        fft, ifft = self.run_validate_fft(a_, b, axes, 
                create_array_copies=False)        
        self.assertTrue(fft.input_alignment == input_dtype_alignment)
        self.assertTrue(fft.output_alignment == output_dtype_alignment)

        a_[:] = a_orig        
        fft, ifft = self.run_validate_fft(a_, b_, axes, 
                create_array_copies=False)        
        self.assertTrue(fft.input_alignment == input_dtype_alignment)
        self.assertTrue(fft.output_alignment == output_dtype_alignment)

        a[:] = a_orig        
        fft, ifft = self.run_validate_fft(a, b, axes, 
                create_array_copies=False, force_unaligned_data=True)
        self.assertTrue(fft.input_alignment == input_dtype_alignment)
        self.assertTrue(fft.output_alignment == output_dtype_alignment)
    
    def test_incorrect_byte_alignment_fails(self):
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']

        input_dtype_alignment = self.get_input_dtype_alignment()
        
        axes=(-1,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        a = n_byte_align(a, 16)
        b = n_byte_align(b, 16)

        fft, ifft = self.run_validate_fft(a, b, axes, 
                force_unaligned_data=True)

        a, b = self.create_test_arrays(in_shape, out_shape)

        # Offset from 16 byte aligned to guarantee it's not
        # 16 byte aligned
        a__ = n_byte_align_empty(
                numpy.prod(in_shape)*a.itemsize + 1, 
                16, dtype='int8')
        
        a_ = a__[1:].view(dtype=self.input_dtype).reshape(*in_shape)
        a_[:] = a 
        
        b__ = n_byte_align_empty(
                numpy.prod(out_shape)*b.itemsize + 1, 
                16, dtype='int8')
        
        b_ = b__[1:].view(dtype=self.output_dtype).reshape(*out_shape)
        b_[:] = b

        self.assertRaisesRegexp(ValueError, 'Invalid output alignment',
                FFTW, *(a, b_))

        self.assertRaisesRegexp(ValueError, 'Invalid input alignment',
                FFTW, *(a_, b))

        self.assertRaisesRegexp(ValueError, 'Invalid input alignment',
                FFTW, *(a_, b_))

    def test_zero_length_fft_axis_fail(self):
        
        in_shape = (1024, 0)
        out_shape = in_shape

        axes = (-1,)

        a, b = self.create_test_arrays(in_shape, out_shape)

        self.assertRaisesRegexp(ValueError, 'Zero length array',
                self.run_validate_fft, *(a,b, axes))

    def test_missized_fail(self):
        in_shape = self.input_shapes['2d']
        _out_shape = self.output_shapes['2d']

        out_shape = (_out_shape[0]+1, _out_shape[1])
        
        axes=(0,)
        a, b = self.create_test_arrays(in_shape, out_shape)
    
        with self.assertRaisesRegexp(ValueError, 'Invalid shapes'):
                FFTW(a, b, axes, direction=self.direction)

    def test_missized_nonfft_axes_fail(self):
        in_shape = self.input_shapes['3d']
        _out_shape = self.output_shapes['3d']
        out_shape = (_out_shape[0], _out_shape[1]+1, _out_shape[2])
        
        axes=(2,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        with self.assertRaisesRegexp(ValueError, 'Invalid shapes'):
                FFTW(a, b, direction=self.direction)

    def test_extra_dimension_fail(self):
        in_shape = self.input_shapes['2d']
        _out_shape = self.output_shapes['2d']        
        out_shape = (2, _out_shape[0], _out_shape[1])
        
        axes=(1,)
        a, b = self.create_test_arrays(in_shape, out_shape)
    
        with self.assertRaisesRegexp(ValueError, 'Invalid shapes'):
                FFTW(a, b, direction=self.direction)
        
    def test_f_contiguous_1d(self):
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']
        
        axes=(0,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        # Taking the transpose just makes the array F contiguous
        a = a.transpose()
        b = b.transpose()

        self.run_validate_fft(a, b, axes, create_array_copies=False)

    def test_different_dtypes_fail(self):
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']
        
        axes=(-1,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        a_ = numpy.complex64(a)
        b_ = numpy.complex128(b)
        self.assertRaisesRegexp(ValueError, 'Invalid scheme',
                FFTW, *(a_,b_))

        a_ = numpy.complex128(a)
        b_ = numpy.complex64(b)
        self.assertRaisesRegexp(ValueError, 'Invalid scheme',
                FFTW, *(a_,b_))
        
    def test_update_data(self):
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']
        
        axes=(-1,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        fft, ifft = self.run_validate_fft(a, b, axes)

        a, b = self.create_test_arrays(in_shape, out_shape)
        
        self.run_validate_fft(a, b, axes, fft=fft, ifft=ifft)
    
    def test_with_not_ndarray_error(self):
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']
        
        a, b = self.create_test_arrays(in_shape, out_shape)

        self.assertRaisesRegexp(ValueError, 'Invalid output array',
                FFTW, *(a,10))

        self.assertRaisesRegexp(ValueError, 'Invalid input array',
                FFTW, *(10,b))

    def test_update_data_with_not_ndarray_error(self):
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']
        
        axes=(-1,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        fft, ifft = self.run_validate_fft(a, b, axes, 
                create_array_copies=False)

        self.assertRaisesRegexp(ValueError, 'Invalid output array',
                fft.update_arrays, *(a,10))

        self.assertRaisesRegexp(ValueError, 'Invalid input array',
                fft.update_arrays, *(10,b))

    def test_update_data_with_stride_error(self):
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']
        
        axes=(-1,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        fft, ifft = self.run_validate_fft(a, b, axes, 
                create_array_copies=False)

        # We offset by 16 to make sure the byte alignment is still correct.
        in_shape = (in_shape[0]+16, in_shape[1]+16)
        out_shape = (out_shape[0]+16, out_shape[1]+16)

        a_, b_ = self.create_test_arrays(in_shape, out_shape)

        a_ = a_[16:,16:]
        b_ = b_[16:,16:]

        with self.assertRaisesRegexp(ValueError, 'Invalid input striding'):
            self.run_validate_fft(a_, b, axes, 
                    fft=fft, ifft=ifft, create_array_copies=False)

        with self.assertRaisesRegexp(ValueError, 'Invalid output striding'):
            self.run_validate_fft(a, b_, axes, 
                    fft=fft, ifft=ifft, create_array_copies=False)

    def test_update_data_with_shape_error(self):
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']
        
        axes=(-1,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        fft, ifft = self.run_validate_fft(a, b, axes)

        in_shape = (in_shape[0]-10, in_shape[1])
        out_shape = (out_shape[0], out_shape[1]+5)

        a_, b_ = self.create_test_arrays(in_shape, out_shape)

        with self.assertRaisesRegexp(ValueError, 'Invalid input shape'):
            self.run_validate_fft(a_, b, axes, 
                    fft=fft, ifft=ifft, create_array_copies=False)

        with self.assertRaisesRegexp(ValueError, 'Invalid output shape'):
            self.run_validate_fft(a, b_, axes, 
                    fft=fft, ifft=ifft, create_array_copies=False)

    def test_update_unaligned_data_with_FFTW_UNALIGNED(self):
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']

        input_dtype_alignment = self.get_input_dtype_alignment()
        
        axes=(-1,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        a = n_byte_align(a, 16)
        b = n_byte_align(b, 16)

        fft, ifft = self.run_validate_fft(a, b, axes, 
                force_unaligned_data=True)

        a, b = self.create_test_arrays(in_shape, out_shape)

        # Offset from 16 byte aligned to guarantee it's not
        # 16 byte aligned
        a__ = n_byte_align_empty(
                numpy.prod(in_shape)*a.itemsize + input_dtype_alignment, 
                16, dtype='int8')
        
        a_ = (a__[input_dtype_alignment:]
                .view(dtype=self.input_dtype).reshape(*in_shape))
        a_[:] = a 
        
        b__ = n_byte_align_empty(
                numpy.prod(out_shape)*b.itemsize + input_dtype_alignment, 
                16, dtype='int8')
        
        b_ = (b__[input_dtype_alignment:]
                .view(dtype=self.output_dtype).reshape(*out_shape))
        b_[:] = b

        self.run_validate_fft(a, b_, axes, fft=fft, ifft=ifft)
        self.run_validate_fft(a_, b, axes, fft=fft, ifft=ifft)
        self.run_validate_fft(a_, b_, axes, fft=fft, ifft=ifft)

    def test_update_data_with_unaligned_original(self):
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']

        input_dtype_alignment = self.get_input_dtype_alignment()
        
        axes=(-1,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        # Offset from 16 byte aligned to guarantee it's not
        # 16 byte aligned
        a__ = n_byte_align_empty(
                numpy.prod(in_shape)*a.itemsize + input_dtype_alignment,
                16, dtype='int8')
        
        a_ = a__[input_dtype_alignment:].view(dtype=self.input_dtype).reshape(*in_shape)
        a_[:] = a
        
        b__ = n_byte_align_empty(
                numpy.prod(out_shape)*b.itemsize + input_dtype_alignment, 
                16, dtype='int8')
        
        b_ = b__[input_dtype_alignment:].view(dtype=self.output_dtype).reshape(*out_shape)
        b_[:] = b
        
        fft, ifft = self.run_validate_fft(a_, b_, axes, 
                force_unaligned_data=True)
        
        self.run_validate_fft(a, b_, axes, fft=fft, ifft=ifft)
        self.run_validate_fft(a_, b, axes, fft=fft, ifft=ifft)
        self.run_validate_fft(a_, b_, axes, fft=fft, ifft=ifft)


    def test_update_data_with_alignment_error(self):
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']

        byte_error = 1
        
        axes=(-1,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        a = n_byte_align(a, 16)
        b = n_byte_align(b, 16)

        fft, ifft = self.run_validate_fft(a, b, axes)
        
        a, b = self.create_test_arrays(in_shape, out_shape)

        # Offset from 16 byte aligned to guarantee it's not
        # 16 byte aligned
        a__ = n_byte_align_empty(
                numpy.prod(in_shape)*a.itemsize+byte_error, 
                16, dtype='int8')
        
        a_ = (a__[byte_error:]
                .view(dtype=self.input_dtype).reshape(*in_shape))
        a_[:] = a 
        
        b__ = n_byte_align_empty(
                numpy.prod(out_shape)*b.itemsize+byte_error, 
                16, dtype='int8')
        
        b_ = (b__[byte_error:]
                .view(dtype=self.output_dtype).reshape(*out_shape))
        b_[:] = b
     
        with self.assertRaisesRegexp(ValueError, 'Invalid output alignment'):
            self.run_validate_fft(a, b_, axes, fft=fft, ifft=ifft, 
                    create_array_copies=False)

        with self.assertRaisesRegexp(ValueError, 'Invalid input alignment'):
            self.run_validate_fft(a_, b, axes, fft=fft, ifft=ifft, 
                    create_array_copies=False)

        # Should also be true for the unaligned case
        fft, ifft = self.run_validate_fft(a, b, axes, 
                force_unaligned_data=True)

        with self.assertRaisesRegexp(ValueError, 'Invalid output alignment'):
            self.run_validate_fft(a, b_, axes, fft=fft, ifft=ifft, 
                    create_array_copies=False)

        with self.assertRaisesRegexp(ValueError, 'Invalid input alignment'):
            self.run_validate_fft(a_, b, axes, fft=fft, ifft=ifft, 
                    create_array_copies=False)

    def test_invalid_axes(self):
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']
        
        axes=(-3,)
        a, b = self.create_test_arrays(in_shape, out_shape)

        with self.assertRaisesRegexp(IndexError, 'Invalid axes'):
                FFTW(a, b, axes, direction=self.direction)

        axes=(10,)
        with self.assertRaisesRegexp(IndexError, 'Invalid axes'):
                FFTW(a, b, axes, direction=self.direction)


class Complex64FFTWTest(Complex64FFTW1DTest, FFTWBaseTest):
        
    def test_2d(self):
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']
        
        axes=(-2,-1)
        a, b = self.create_test_arrays(in_shape, out_shape)

        self.run_validate_fft(a, b, axes, create_array_copies=False)
           
    def test_multiple_2d(self):
        in_shape = self.input_shapes['3d']
        out_shape = self.output_shapes['3d']
        
        axes=(-2,-1)
        a, b = self.create_test_arrays(in_shape, out_shape)

        self.run_validate_fft(a, b, axes, create_array_copies=False)
        
    def test_3d(self):
        in_shape = self.input_shapes['3d']
        out_shape = self.output_shapes['3d']
        
        axes=(0, 1, 2)
        a, b = self.create_test_arrays(in_shape, out_shape)

        self.run_validate_fft(a, b, axes, create_array_copies=False)
        
    def test_non_monotonic_increasing_axes(self):
        '''Test the case where the axes arg does not monotonically increase.
        '''
        axes=(1, 0)

        # We still need the shapes to work!
        in_shape = numpy.asarray(self.input_shapes['2d'])[list(axes)]
        out_shape = numpy.asarray(self.output_shapes['2d'])[list(axes)]
        
        a, b = self.create_test_arrays(in_shape, out_shape, axes=axes)

        self.run_validate_fft(a, b, axes, create_array_copies=False)
        
    def test_non_contiguous_2d(self):
        in_shape = self.input_shapes['2d']
        out_shape = self.output_shapes['2d']
        
        axes=(-2,-1)
        a, b = self.create_test_arrays(in_shape, out_shape)

        # Some arbitrary and crazy slicing
        a_sliced = a[12:200:3, 300:2041:9]
        # b needs to be the same size
        b_sliced = b[20:146:2, 100:1458:7]

        self.run_validate_fft(a_sliced, b_sliced, axes, create_array_copies=False)
        
    def test_non_contiguous_2d_in_3d(self):
        in_shape = (256, 4, 2048)
        out_shape = in_shape
        axes=(0,2)
        a, b = self.create_test_arrays(in_shape, out_shape)

        # Some arbitrary and crazy slicing
        a_sliced = a[12:200:3, :, 300:2041:9]
        # b needs to be the same size
        b_sliced = b[20:146:2, :, 100:1458:7]

        self.run_validate_fft(a_sliced, b_sliced, axes, create_array_copies=False)


class Complex128FFTWTest(Complex64FFTWTest):
    
    def setUp(self):

        self.input_dtype = numpy.complex128
        self.output_dtype = numpy.complex128
        self.np_fft_comparison = numpy.fft.fft

        self.direction = 'FFTW_FORWARD'
        return

class ComplexLongDoubleFFTWTest(Complex64FFTWTest):
    
    def setUp(self):

        self.input_dtype = numpy.clongdouble
        self.output_dtype = numpy.clongdouble
        self.np_fft_comparison = self.reference_fftn

        self.direction = 'FFTW_FORWARD'        
        return

    def reference_fftn(self, a, axes):

        # numpy.fft.fftn doesn't support complex256 type,
        # so we need to compare to a lower precision type.
        a = numpy.complex128(a)
        return numpy.fft.fftn(a, axes=axes)

    @unittest.skip('numpy.fft has issues with this dtype.')
    def test_time(self):
        pass

    @unittest.skip('numpy.fft has issues with this dtype.')    
    def test_time_with_array_update(self):
        pass

test_cases = (
        Complex64FFTWTest,
        Complex128FFTWTest,
        ComplexLongDoubleFFTWTest,)

test_set = None
#test_set = {'all':['test_alignment']}

if __name__ == '__main__':
    run_test_suites(test_cases, test_set)

