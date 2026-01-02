using Bonsai;
using System;
using System.ComponentModel;
using System.Collections.Generic;
using System.Linq;
using System.Reactive.Linq;

[Combinator]
[Description("Parses lines, splitting at the first comma.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class ParseSettingCsv
{
   public IObservable<Dictionary<string, string>> Process(IObservable<string> source)
    {
        return source.Select(value =>
        {
            // split into lines
            var lines = value.Split(new[] { "\r\n", "\n" }, StringSplitOptions.RemoveEmptyEntries);
            
            var settings = new Dictionary<string, string>();
            foreach (var line in lines)
            {
                int commaIndex = line.IndexOf(',');
                if (commaIndex >= 0)    // skip if no comma in line
                {
                    string key = line.Substring(0, commaIndex);
                    string val = line.Substring(commaIndex + 1);
                    settings[key] = val;
                }
            }

            return settings;
        });
    }
}