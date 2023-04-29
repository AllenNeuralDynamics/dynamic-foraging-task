using Bonsai;
using System;
using System.ComponentModel;
using System.Collections.Generic;
using System.Linq;
using System.Reactive.Linq;
using Bonsai.Osc;

[Combinator]
[Description("")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class OscToCsv
{

    public IObservable<OscCsvElement> Process(IObservable<Message> source)
    {
        return source.Select(value =>  new OscCsvElement(){ Address = value.Address.Replace("/", ""), TypeTag = value.TypeTag.Remove(0,1), Message = string.Join(",", value.GetContents().Cast<object>())});
    }
}
public struct OscCsvElement
{
    public string Address;
    public string TypeTag;
    public string Message;


}
