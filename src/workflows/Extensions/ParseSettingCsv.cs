using Bonsai;
using System;
using System.ComponentModel;
using System.Collections.Generic;
using System.Linq;
using System.Reactive.Linq;
using System.IO;
using CsvHelper;
using System.Globalization;

[Combinator]
[Description("Parses CSV synchronously.")]
[WorkflowElementCategory(ElementCategory.Transform)]
public class ParseSettingCsv
{
   public IObservable<Dictionary<string, string>> Process(IObservable<string> source)
    {
        return source.Select(value =>
        {
            var settings = new Dictionary<string, string>();

            using (var reader = new StringReader(value))
            using (var csv = new CsvReader(reader, CultureInfo.InvariantCulture))
            {
                while (csv.Read())
                {
                    var key = csv.GetField(0);
                    var val = csv.GetField(1);
                    settings[key] = val;
                }
            }

            return settings;

        });
    }
}