using System.Text.Json;
using Build.Models;

namespace Build.Helpers;

public static class ProductDataHelper
{
    public static List<ProductRecord> LoadProducts(string path)
    {
        if (!File.Exists(path))
        {
            return [];
        }

        var json = File.ReadAllText(path);
        return JsonSerializer.Deserialize<List<ProductRecord>>(json) ?? [];
    }

    public static void SaveProducts(string path, IEnumerable<ProductRecord> products)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var json = JsonSerializer.Serialize(products, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(path, json);
    }

    public static void InsertProduct(List<ProductRecord> products, ProductRecord product, bool cli, bool msi = false)
    {
        if (products.Any(x => x.Product == product.Product && x.Version == product.Version))
        {
            throw new InvalidOperationException($"{product.Product} product already exists with version {product.Version}");
        }

        if (cli)
        {
            var firstCliIndex = products.FindIndex(x => x.Product.Contains("CLI", StringComparison.Ordinal));
            var index = firstCliIndex >= 0 ? firstCliIndex : products.FindIndex(x => x.Product != "pyRevit");
            if (index < 0)
            {
                index = products.Count;
            }

            products.Insert(index, product);
            return;
        }

        products.Insert(0, product);
    }
}
