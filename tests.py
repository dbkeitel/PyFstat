import unittest
import numpy as np
import os
import shutil
import pyfstat
import lalpulsar


class Test(unittest.TestCase):
    outdir = 'TestData'

    @classmethod
    def setUpClass(self):
        if os.path.isdir(self.outdir):
            shutil.rmtree(self.outdir)

    @classmethod
    def tearDownClass(self):
        if os.path.isdir(self.outdir):
            shutil.rmtree(self.outdir)


class TestWriter(Test):
    label = "TestWriter"

    def test_make_cff(self):
        Writer = pyfstat.Writer(self.label, outdir=self.outdir)
        Writer.make_cff()
        self.assertTrue(os.path.isfile(
            './{}/{}.cff'.format(self.outdir, self.label)))

    def test_run_makefakedata(self):
        Writer = pyfstat.Writer(self.label, outdir=self.outdir, duration=3600)
        Writer.make_cff()
        Writer.run_makefakedata()
        self.assertTrue(os.path.isfile(
            './{}/H-2_H1_1800SFT_TestWriter-700000000-3600.sft'
            .format(self.outdir)))

    def test_makefakedata_usecached(self):
        Writer = pyfstat.Writer(self.label, outdir=self.outdir, duration=3600)
        if os.path.isfile(Writer.sftfilepath):
            os.remove(Writer.sftfilepath)
        Writer.make_cff()
        Writer.run_makefakedata()
        time_first = os.path.getmtime(Writer.sftfilepath)
        Writer.run_makefakedata()
        time_second = os.path.getmtime(Writer.sftfilepath)
        self.assertTrue(time_first == time_second)
        os.system('touch {}'.format(Writer.config_file_name))
        Writer.run_makefakedata()
        time_third = os.path.getmtime(Writer.sftfilepath)
        self.assertFalse(time_first == time_third)


class TestBunch(Test):
    def test_bunch(self):
        b = pyfstat.core.Bunch(dict(x=10))
        self.assertTrue(b.x == 10)


class Test_par(Test):
    label = 'TestPar'

    def test(self):
        os.system('mkdir {}'.format(self.outdir))
        os.system(
            'echo "x=100\ny=10" > {}/{}.par'.format(self.outdir, self.label))

        par = pyfstat.core.read_par(
            '{}/{}.par'.format(self.outdir, self.label), return_type='Bunch')
        self.assertTrue(par.x == 100)
        self.assertTrue(par.y == 10)

        par = pyfstat.core.read_par(outdir=self.outdir, label=self.label,
                                    return_type='dict')
        self.assertTrue(par['x'] == 100)
        self.assertTrue(par['y'] == 10)
        os.system('rm -r {}'.format(self.outdir))


class TestBaseSearchClass(Test):
    def test_shift_matrix(self):
        BSC = pyfstat.BaseSearchClass()
        dT = 10
        a = BSC._shift_matrix(4, dT)
        b = np.array([[1, 2*np.pi*dT, 2*np.pi*dT**2/2.0, 2*np.pi*dT**3/6.0],
                      [0, 1, dT, dT**2/2.0],
                      [0, 0, 1, dT],
                      [0, 0, 0, 1]])
        self.assertTrue(np.array_equal(a, b))

    def test_shift_coefficients(self):
        BSC = pyfstat.BaseSearchClass()
        thetaA = np.array([10., 1e2, 10., 1e2])
        dT = 100

        # Calculate the 'long' way
        thetaB = np.zeros(len(thetaA))
        thetaB[3] = thetaA[3]
        thetaB[2] = thetaA[2] + thetaA[3]*dT
        thetaB[1] = thetaA[1] + thetaA[2]*dT + .5*thetaA[3]*dT**2
        thetaB[0] = thetaA[0] + 2*np.pi*(thetaA[1]*dT + .5*thetaA[2]*dT**2
                                         + thetaA[3]*dT**3 / 6.0)

        self.assertTrue(
            np.array_equal(
                thetaB, BSC._shift_coefficients(thetaA, dT)))

    def test_shift_coefficients_loop(self):
        BSC = pyfstat.BaseSearchClass()
        thetaA = np.array([10., 1e2, 10., 1e2])
        dT = 1e1
        thetaB = BSC._shift_coefficients(thetaA, dT)
        self.assertTrue(
            np.allclose(
                thetaA, BSC._shift_coefficients(thetaB, -dT),
                rtol=1e-9, atol=1e-9))


class TestComputeFstat(Test):
    label = "TestComputeFstat"

    def test_run_computefstatistic_single_point(self):
        Writer = pyfstat.Writer(self.label, outdir=self.outdir, duration=86400,
                                h0=1, sqrtSX=1, detectors='H1,L1')
        Writer.make_data()
        predicted_FS = Writer.predict_fstat()

        search_H1L1 = pyfstat.ComputeFstat(
            tref=Writer.tref,
            sftfilepattern='{}/*{}*sft'.format(Writer.outdir, Writer.label))
        FS = search_H1L1.get_fullycoherent_twoF(
            Writer.tstart, Writer.tend, Writer.F0, Writer.F1, Writer.F2,
            Writer.Alpha, Writer.Delta)
        self.assertTrue(np.abs(predicted_FS-FS)/FS < 0.2)

        Writer.detectors = 'H1'
        predicted_FS = Writer.predict_fstat()
        search_H1 = pyfstat.ComputeFstat(
            tref=Writer.tref, detectors='H1',
            sftfilepattern='{}/*{}*sft'.format(Writer.outdir, Writer.label),
            SSBprec=lalpulsar.SSBPREC_RELATIVISTIC)
        FS = search_H1.get_fullycoherent_twoF(
            Writer.tstart, Writer.tend, Writer.F0, Writer.F1, Writer.F2,
            Writer.Alpha, Writer.Delta)
        self.assertTrue(np.abs(predicted_FS-FS)/FS < 0.2)

    def run_computefstatistic_single_point_no_noise(self):
        Writer = pyfstat.Writer(
            self.label, outdir=self.outdir, add_noise=False, duration=86400,
            h0=1, sqrtSX=1)
        Writer.make_data()
        predicted_FS = Writer.predict_fstat()

        search = pyfstat.ComputeFstat(
            tref=Writer.tref, assumeSqrtSX=1,
            sftfilepattern='{}/*{}*sft'.format(Writer.outdir, Writer.label))
        FS = search.get_fullycoherent_twoF(
            Writer.tstart, Writer.tend, Writer.F0, Writer.F1, Writer.F2,
            Writer.Alpha, Writer.Delta)
        self.assertTrue(np.abs(predicted_FS-FS)/FS < 0.3)

    def test_injectSources(self):
        # This seems to be writing with a signal...
        Writer = pyfstat.Writer(
            self.label, outdir=self.outdir, add_noise=False, duration=86400,
            h0=1, sqrtSX=1)
        Writer.make_cff()
        injectSources = Writer.config_file_name

        search = pyfstat.ComputeFstat(
            tref=Writer.tref, assumeSqrtSX=1, injectSources=injectSources,
            minCoverFreq=28, maxCoverFreq=32, minStartTime=Writer.tstart,
            maxStartTime=Writer.tstart+Writer.duration,
            detectors=Writer.detectors)
        FS_from_file = search.get_fullycoherent_twoF(
            Writer.tstart, Writer.tend, Writer.F0, Writer.F1, Writer.F2,
            Writer.Alpha, Writer.Delta)
        Writer.make_data()
        predicted_FS = Writer.predict_fstat()
        self.assertTrue(np.abs(predicted_FS-FS_from_file)/FS_from_file < 0.2)

        injectSourcesdict = pyfstat.core.read_par(Writer.config_file_name)
        injectSourcesdict['F0'] = injectSourcesdict['Freq']
        injectSourcesdict['F1'] = injectSourcesdict['f1dot']
        injectSourcesdict['F2'] = injectSourcesdict['f2dot']
        search = pyfstat.ComputeFstat(
            tref=Writer.tref, assumeSqrtSX=1, injectSources=injectSourcesdict,
            minCoverFreq=28, maxCoverFreq=32, minStartTime=Writer.tstart,
            maxStartTime=Writer.tstart+Writer.duration,
            detectors=Writer.detectors)
        FS_from_dict = search.get_fullycoherent_twoF(
            Writer.tstart, Writer.tend, Writer.F0, Writer.F1, Writer.F2,
            Writer.Alpha, Writer.Delta)
        self.assertTrue(FS_from_dict == FS_from_file)


class TestSemiCoherentSearch(Test):
    label = "TestSemiCoherentSearch"

    def test_get_semicoherent_twoF(self):
        duration = 10*86400
        Writer = pyfstat.Writer(
            self.label, outdir=self.outdir, duration=duration, h0=1, sqrtSX=1)
        Writer.make_data()

        search = pyfstat.SemiCoherentSearch(
            label=self.label, outdir=self.outdir, nsegs=2,
            sftfilepattern='{}/*{}*sft'.format(Writer.outdir, Writer.label),
            tref=Writer.tref, minStartTime=Writer.tstart,
            maxStartTime=Writer.tend)

        search.get_semicoherent_twoF(
            Writer.F0, Writer.F1, Writer.F2, Writer.Alpha, Writer.Delta,
            record_segments=True)

        # Compute the predicted semi-coherent Fstat
        minStartTime = Writer.tstart
        maxStartTime = Writer.tend

        Writer.maxStartTime = minStartTime + duration / 2.0
        FSA = Writer.predict_fstat()

        Writer.tstart = minStartTime + duration / 2.0
        Writer.tend = maxStartTime
        FSB = Writer.predict_fstat()

        FSs = np.array([FSA, FSB])
        diffs = (np.array(search.detStat_per_segment) - FSs) / FSs
        self.assertTrue(np.all(diffs < 0.3))

    def test_get_semicoherent_BSGL(self):
        duration = 10*86400
        Writer = pyfstat.Writer(
            self.label, outdir=self.outdir, duration=duration,
            detectors='H1,L1')
        Writer.make_data()

        search = pyfstat.SemiCoherentSearch(
            label=self.label, outdir=self.outdir, nsegs=2,
            sftfilepattern='{}/*{}*sft'.format(Writer.outdir, Writer.label),
            tref=Writer.tref, minStartTime=Writer.tstart,
            maxStartTime=Writer.tend, BSGL=True)

        BSGL = search.get_semicoherent_twoF(
            Writer.F0, Writer.F1, Writer.F2, Writer.Alpha, Writer.Delta,
            record_segments=True)
        self.assertTrue(BSGL > 0)


class TestSemiCoherentGlitchSearch(Test):
    label = "TestSemiCoherentGlitchSearch"

    def test_get_semicoherent_nglitch_twoF(self):
        duration = 10*86400
        dtglitch = .5*duration
        delta_F0 = 0
        h0 = 1
        sqrtSX = 1
        Writer = pyfstat.GlitchWriter(
            self.label, outdir=self.outdir, duration=duration, dtglitch=dtglitch,
            delta_F0=delta_F0, sqrtSX=sqrtSX, h0=h0)

        Writer.make_data()

        search = pyfstat.SemiCoherentGlitchSearch(
            label=self.label, outdir=self.outdir,
            sftfilepattern='{}/*{}*sft'.format(Writer.outdir, Writer.label),
            tref=Writer.tref, minStartTime=Writer.tstart,
            maxStartTime=Writer.tend, nglitch=1)

        FS = search.get_semicoherent_nglitch_twoF(
            Writer.F0, Writer.F1, Writer.F2, Writer.Alpha, Writer.Delta,
            Writer.delta_F0, Writer.delta_F1, search.minStartTime+dtglitch)

        # Compute the predicted semi-coherent glitch Fstat
        minStartTime = Writer.tstart
        maxStartTime = Writer.tend

        Writer.maxStartTime = minStartTime + dtglitch
        FSA = Writer.predict_fstat()

        Writer.tstart = minStartTime + dtglitch
        Writer.tend = maxStartTime
        FSB = Writer.predict_fstat()

        print FSA, FSB
        predicted_FS = (FSA + FSB)

        print(predicted_FS, FS)
        self.assertTrue(np.abs((FS - predicted_FS))/predicted_FS < 0.3)


class TestMCMCSearch(Test):
    label = "TestMCMCSearch"

    def test_fully_coherent(self):
        h0 = 1
        sqrtSX = 1
        F0 = 30
        F1 = -1e-10
        F2 = 0
        minStartTime = 700000000
        duration = 1 * 86400
        maxStartTime = minStartTime + duration
        Alpha = 5e-3
        Delta = 1.2
        tref = minStartTime
        Writer = pyfstat.Writer(F0=F0, F1=F1, F2=F2, label=self.label,
                                h0=h0, sqrtSX=sqrtSX,
                                outdir=self.outdir, tstart=minStartTime,
                                Alpha=Alpha, Delta=Delta, tref=tref,
                                duration=duration,
                                Band=4)

        Writer.make_data()
        predicted_FS = Writer.predict_fstat()

        theta = {'F0': {'type': 'norm', 'loc': F0, 'scale': np.abs(1e-10*F0)},
                 'F1': {'type': 'norm', 'loc': F1, 'scale': np.abs(1e-10*F1)},
                 'F2': F2, 'Alpha': Alpha, 'Delta': Delta}

        search = pyfstat.MCMCSearch(
            label=self.label, outdir=self.outdir, theta_prior=theta, tref=tref,
            sftfilepattern='{}/*{}*sft'.format(Writer.outdir, Writer.label),
            minStartTime=minStartTime, maxStartTime=maxStartTime,
            nsteps=[100, 100], nwalkers=100, ntemps=2, log10beta_min=-1)
        search.setup_burnin_convergence_testing()
        search.run(create_plots=False)
        _, FS = search.get_max_twoF()

        print('Predicted twoF is {} while recovered is {}'.format(
                predicted_FS, FS))
        self.assertTrue(
            FS > predicted_FS or np.abs((FS-predicted_FS))/predicted_FS < 0.3)


if __name__ == '__main__':
    unittest.main()
