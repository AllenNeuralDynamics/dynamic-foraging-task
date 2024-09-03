using Bonsai;
using System;
using Bonsai.Vision.Design;
using OpenTK.Graphics.OpenGL;
using OpenCV.Net;
using System.Windows.Forms;
using Bonsai.Design.Visualizers;

[assembly: TypeVisualizer(typeof(IplImageRotateVisualizer), Target = typeof(IplImage))]

public class IplImageRotateVisualizer : IplImageVisualizer
{
    ToolStripButton invertHorizontalButton;
    ToolStripButton invertVerticalButton;

    ToolStripComboBox angleComboBoxButton;

    public bool InvertHorizontal { get; set; }
    public bool InvertVertical { get; set; }
    public float RotateAngle { get; set; }

    public override void Load(IServiceProvider provider)
    {
        base.Load(provider);
        invertHorizontalButton = new ToolStripButton("Invert Horizontal");
        invertHorizontalButton.CheckState = CheckState.Checked;
        invertHorizontalButton.Checked = InvertHorizontal;
        invertHorizontalButton.CheckOnClick = true;
        invertHorizontalButton.CheckedChanged += (sender, e) => InvertHorizontal = invertHorizontalButton.Checked;
        StatusStrip.Items.Add(invertHorizontalButton);

        invertVerticalButton = new ToolStripButton("Invert Vertical");
        invertVerticalButton.CheckState = CheckState.Checked;
        invertVerticalButton.Checked = InvertVertical;
        invertVerticalButton.CheckOnClick = true;
        invertVerticalButton.CheckedChanged += (sender, e) => InvertVertical = invertVerticalButton.Checked;
        StatusStrip.Items.Add(invertVerticalButton);

        angleComboBoxButton = new ToolStripComboBox();
        angleComboBoxButton.Items.AddRange(new object[] {
            0,
            90,
            180,
            270,
        });
        angleComboBoxButton.SelectedIndex = 0;
        angleComboBoxButton.SelectedIndexChanged += (sender, e) => RotateAngle = Convert.ToSingle(angleComboBoxButton.SelectedItem);
        angleComboBoxButton.Name = "RotationAngle";
        StatusStrip.Items.Add(angleComboBoxButton);

        VisualizerCanvas.Load += (sender, e) =>
            {
                GL.Enable(EnableCap.Blend);
                GL.Enable(EnableCap.PointSmooth);
                GL.BlendFunc(BlendingFactor.SrcAlpha, BlendingFactor.OneMinusSrcAlpha);
            };
    }

    protected override void RenderFrame()
    {
        var invertHorizontal = InvertHorizontal;
        var invertVertical = InvertVertical;

        GL.PushMatrix();
        if (InvertHorizontal){
		    GL.Scale(-1,1,1);
        }
        if (InvertVertical){
		    GL.Scale(1,-1,1);
        }
        GL.Rotate(RotateAngle, OpenTK.Vector3d.UnitZ); // Rotates image
        base.RenderFrame();
        GL.PopMatrix();
    }
}
