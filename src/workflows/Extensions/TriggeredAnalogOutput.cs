using System;
using System.Reactive.Linq;
using OpenCV.Net;
using NationalInstruments.DAQmx;
using System.Runtime.InteropServices;
using System.Reactive.Disposables;
using System.Collections.ObjectModel;
using System.ComponentModel;

namespace Bonsai.DAQmx
{
    /// <summary>
    /// Represents an operator that generates voltage signals in one or more DAQmx analog
    /// output channels from a sequence of sample buffers.
    /// </summary>
    [DefaultProperty("Channel")]
    [Description("Generates voltage signals in one or more DAQmx analog output channels from a sequence of sample buffers.")]
    public class TriggeredAnalogOutput : Sink<Mat>
    {
        readonly Collection<AnalogOutputChannelConfiguration> channels = new Collection<AnalogOutputChannelConfiguration>();

        /// <summary>
        /// Gets or sets the optional source terminal of the clock. If not specified,
        /// the internal clock of the device will be used.
        /// </summary>
        [Description("The optional source terminal of the clock. If not specified, the internal clock of the device will be used.")]
        private string signalSource = string.Empty;
        public string SignalSource
        {
            get { return signalSource; }
            set { signalSource = value; }
        }
        
        /// <summary>
        /// Gets or sets the optional source terminal of the trigger.
        /// </summary>
        [Description("The optional source terminal of the clock. If not specified, the internal clock of the device will be used.")]
        private string triggerSource = string.Empty;
        public string TriggerSource
        {
            get { return triggerSource; }
            set { triggerSource = value; }
        }

        /// <summary>
        /// Gets or sets the sampling rate for generating voltage signals, in samples
        /// per second.
        /// </summary>
        [Description("The sampling rate for generating voltage signals, in samples per second.")]
        public double SampleRate { get; set; }

        /// <summary>
        /// Gets or sets a value specifying on which edge of a clock pulse sampling takes place.
        /// </summary>
        [Description("Specifies on which edge of a clock pulse sampling takes place.")]
        private SampleClockActiveEdge activeEdge = SampleClockActiveEdge.Rising;
        public SampleClockActiveEdge ActiveEdge
        {
            get { return activeEdge; }
            set { activeEdge = value; }
        }
        
        /// <summary>
        /// Gets or sets a value specifying whether the signal generation task will generate
        /// a finite number of samples or if it continuously generates samples.
        /// </summary>
        [Description("Specifies whether the signal generation task will generate a finite number of samples or if it continuously generates samples.")]
        private SampleQuantityMode sampleMode = SampleQuantityMode.ContinuousSamples;
        public SampleQuantityMode SampleMode
        {
            get { return sampleMode; }
            set { sampleMode = value; }
        }
        
        /// <summary>
        /// Gets or sets the number of samples to generate, for finite samples, or the
        /// size of the buffer for continuous signal generation.
        /// </summary>
        [Description("The number of samples to generate, for finite samples, or the size of the buffer for continuous signal generation.")]
        private int bufferSize = 1000;
        public int BufferSize
        {
            get { return bufferSize; }
            set { bufferSize = value; }
        }
        

        /// <summary>
        /// Gets the collection of analog output channels used to generate voltage signals.
        /// </summary>
        [Editor("Bonsai.Design.DescriptiveCollectionEditor, Bonsai.Design", DesignTypes.UITypeEditor)]
        [Description("The collection of analog output channels used to generate voltage signals.")]
        public Collection<AnalogOutputChannelConfiguration> Channels
        {
            get { return channels; }
        }

        /// <summary>
        /// Generates voltage signals in one or more DAQmx analog output channels
        /// from an observable sequence of sample buffers.
        /// </summary>
        /// <param name="source">
        /// A sequence of 2D <see cref="Mat"/> objects storing the voltage samples.
        /// Each row corresponds to one of the channels in the signal generation task,
        /// and each column to a sample from each of the channels. The order of the
        /// channels follows the order in which you specify the channels in the
        /// <see cref="Channels"/> property.
        /// </param>
        /// <returns>
        /// An observable sequence that is identical to the <paramref name="source"/>
        /// sequence but where there is an additional side effect of generating
        /// voltage signals in one or more DAQmx analog output channels.
        /// </returns>
        public override IObservable<Mat> Process(IObservable<Mat> source)
        {
            return Observable.Defer(() =>
            {
                var task = new Task();
                foreach (var channel in channels)
                {
                    task.AOChannels.CreateVoltageChannel(channel.PhysicalChannel, channel.ChannelName, channel.MinimumValue, channel.MaximumValue, channel.VoltageUnits);
                }

                task.Control(TaskAction.Verify);
                task.Timing.ConfigureSampleClock(SignalSource, SampleRate, ActiveEdge, SampleMode, BufferSize);
                task.Triggers.StartTrigger.ConfigureDigitalEdgeTrigger(triggerSource, DigitalEdgeStartTriggerEdge.Rising);
                //task.Triggers.StartTrigger.ConfigureAnalogEdgeTrigger(triggerSource, AnalogEdgeStartTriggerSlope.Rising, 1.0);

                var analogOutWriter = new AnalogMultiChannelWriter(task.Stream);
                return Observable.Using(
                    () => Disposable.Create(() =>
                    {
                        if (task.Timing.SampleQuantityMode == SampleQuantityMode.FiniteSamples)
                        {
                            task.WaitUntilDone();
                        }
                        task.Stop();
                        task.Dispose();
                    }),
                    resource => source.Do(input =>
                    {
                        var data = new double[input.Rows, input.Cols];
                        var dataHandle = GCHandle.Alloc(data, GCHandleType.Pinned);
                        try
                        {
                            var dataHeader = new Mat(input.Rows, input.Cols, Depth.F64, 1, dataHandle.AddrOfPinnedObject());
                            if (input.Depth != dataHeader.Depth) CV.Convert(input, dataHeader);
                            else CV.Copy(input, dataHeader);
                            analogOutWriter.WriteMultiSample(true, data);
                        }
                        finally { dataHandle.Free(); }
                    }));
            });
        }
    }
}